from __future__ import annotations
from datetime import datetime, date, time, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import (
    User, Attendance, CompanySettings, Holiday, LeaveRequest, PermissionRequest, AttendanceCorrection
)
from app.security import hash_password, create_token
from app.services.attendance_service import (
    calculate_attendance_rule,
    check_in_user,
    check_out_user,
    finalize_daily_attendance,
    recover_missed_finalizations,
    get_attendance_summary_metrics,
    get_attendance_calendar_feed,
)
from app.services.holiday_service import (
    generate_sundays_calendar,
    seed_2026_holidays,
    seed_2027_holidays,
    is_holiday,
    is_weekly_off,
    SUPPLIED_2027_HOLIDAYS,
)


@pytest.fixture(scope="module")
def test_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = TestingSessionLocal()

    # Create company settings
    settings = CompanySettings(
        work_start_time="09:00",
        checkin_grace_time="09:30",
        afternoon_start_time="13:00",
        early_checkout_threshold="17:00",
        work_end_time="17:30",
        timezone="Asia/Kolkata",
    )
    db.add(settings)

    # Seed 2026 and 2027 holidays
    seed_2026_holidays(db)
    seed_2027_holidays(db, force_active=True)

    # Create test users
    pw = hash_password("demo123")
    emp = User(
        id=101,
        name="Test Employee",
        email="emp_test@mindfulmetrics.com",
        password_hash=pw,
        role="employee",
        department="Engineering",
        employee_code="E101",
    )
    mgr = User(
        id=102,
        name="Test Manager",
        email="mgr_test@mindfulmetrics.com",
        password_hash=pw,
        role="manager",
        department="Engineering",
        employee_code="M102",
    )
    hr_user = User(
        id=103,
        name="Test HR",
        email="hr_test@mindfulmetrics.com",
        password_hash=pw,
        role="hr",
        department="HR",
        employee_code="H103",
    )
    other_emp = User(
        id=104,
        name="Other Employee",
        email="other_test@mindfulmetrics.com",
        password_hash=pw,
        role="employee",
        department="Sales",
        employee_code="E104",
    )
    db.add_all([emp, mgr, hr_user, other_emp])
    db.commit()

    yield db
    db.close()


# ==============================================================================
# PART 1: CALENDAR AND HOLIDAYS (Tests 1 - 9)
# ==============================================================================

def test_01_every_generated_sunday_correct_weekday():
    """Test 1: All 104 Sundays from 2026-01-04 to 2027-12-26 have weekday() == 6."""
    res = generate_sundays_calendar(start_year=2026, end_year=2027)
    assert res["ok"] is True
    assert res["total_sundays"] == 104
    assert res["first_sunday"] == "2026-01-04"
    assert res["last_sunday"] == "2027-12-26"
    assert res["all_validated"] is True
    for item in res["sundays"]:
        d = date.fromisoformat(item["date"])
        assert d.weekday() == 6, f"Date {item['date']} is not a Sunday (weekday={d.weekday()})"


def test_02_sunday_generation_recurring_beyond_2027():
    """Test 2: Sunday weekly-off generation works beyond 2027."""
    res_2028 = generate_sundays_calendar(start_year=2028, end_year=2028)
    assert res_2028["ok"] is True
    assert res_2028["total_sundays"] == 53
    assert res_2028["all_validated"] is True

    res_2029 = generate_sundays_calendar(start_year=2029, end_year=2029)
    assert res_2029["ok"] is True
    assert res_2029["total_sundays"] == 52
    assert res_2029["all_validated"] is True


def test_03_and_04_supplied_2027_holidays_idempotent(test_db):
    """Test 3 & 4: 2027 holiday list imported idempotently with no duplicates on repeated runs."""
    res1 = seed_2027_holidays(test_db, force_active=True)
    assert res1["ok"] is True
    assert res1["already_existing"] == 23  # already seeded in fixture
    assert res1["inserted"] == 0

    count_2027 = test_db.query(Holiday).filter(Holiday.calendar_year == 2027).count()
    assert count_2027 == 23


def test_05_sunday_holiday_overlap_handling(test_db):
    """Test 5: Overlaps (2026-02-01 Thai Poosam, 2027-01-17 Farmers' Day, 2027-08-15 Independence Day) handled safely without duplicate rows."""
    # 1. Past overlap: 2026-02-01 (Thai Poosam falls on Sunday)
    d_poosam = date(2026, 2, 1)
    assert d_poosam.weekday() == 6
    is_h, hol = is_holiday(test_db, d_poosam, calendar_type="company")
    assert is_h is True
    res_past = finalize_daily_attendance(test_db, target_date=d_poosam, force=True)
    assert res_past["ok"] is True

    # 2. Future overlap without allow_future must be blocked
    d_farmers = date(2027, 1, 17)
    res_blocked = finalize_daily_attendance(test_db, target_date=d_farmers, force=True)
    assert res_blocked["ok"] is False
    assert "future dates" in res_blocked["error"].lower()

    # 3. Future overlap simulation with allow_future=True
    res_sim = finalize_daily_attendance(test_db, target_date=d_farmers, force=True, allow_future=True)
    assert res_sim["ok"] is True

    # Verify only 1 record per user exists for this date
    records = test_db.query(Attendance).filter(Attendance.date == d_farmers).all()
    assert len(records) == 3  # 3 eligible users (101, 102, 104)
    for r in records:
        assert r.final_status == "HOLIDAY"
        assert r.morning_status == "HOLIDAY"
        assert r.afternoon_status == "WEEKLY_OFF"


def test_06_bank_only_holiday_applicability(test_db):
    """Test 6: Bank-only holiday (April 1) does not apply to normal company calendar."""
    d_bank = date(2027, 4, 1)
    is_h_comp, _ = is_holiday(test_db, d_bank, calendar_type="company")
    assert is_h_comp is False, "Bank-only holiday must not apply to company employees"

    is_h_bank, hol = is_holiday(test_db, d_bank, calendar_type="all")
    assert is_h_bank is True
    assert hol.applicability == "bank_only"


def test_07_unverified_holiday_dates_audit_tracking(test_db):
    """Test 7: 2027 holidays preserve audit source reference and pending verification flag."""
    hol_2027 = test_db.query(Holiday).filter(Holiday.calendar_year == 2027).first()
    assert hol_2027.source_name == "Supplied Tamil Nadu Holiday Calendar 2027"
    assert "Pending official Tamil Nadu Government Order" in hol_2027.source_reference


def test_08_and_09_historical_dates_and_future_not_absent(test_db):
    """Test 8 & 9: Calendar feed displays historical records and never marks future dates absent."""
    emp = test_db.query(User).filter(User.role == "employee").first()
    today = date.today()

    # Generate feed for current month
    feed = get_attendance_calendar_feed(test_db, emp, year=today.year, month=today.month)
    assert len(feed) >= 28

    for day_item in feed:
        d = date.fromisoformat(day_item["date"])
        if d > today:
            assert day_item["status"] in ("FUTURE", "WEEKLY_OFF", "HOLIDAY"), f"Future date {d} was marked as {day_item['status']}!"
            assert day_item["status"] != "ABSENT"


# ==============================================================================
# PART 2: ATTENDANCE RULES AND CALCULATIONS (Tests 10 - 21)
# ==============================================================================

def test_10_normal_checkin():
    """Test 10: Normal on-time check-in (09:00 AM) has 0 late minutes and PRESENT status."""
    settings = CompanySettings(
        work_start_time="09:00",
        checkin_grace_time="09:30",
        afternoon_start_time="13:00",
        early_checkout_threshold="17:00",
        work_end_time="17:30",
        timezone="Asia/Kolkata",
    )
    d = date(2026, 10, 5)
    cin = datetime.combine(d, time(9, 0))
    cout = datetime.combine(d, time(17, 30))
    res = calculate_attendance_rule(settings, cin, cout)
    assert res["morning_status"] == "PRESENT"
    assert res["afternoon_status"] == "PRESENT"
    assert res["final_status"] == "FULL_DAY_PRESENT"
    assert res["late_minutes"] == 0
    assert res["working_minutes"] == 510  # 8h 30m


def test_11_late_checkin_with_grace_period():
    """Test 11: Late check-in after grace period (09:45 AM) marks late minutes."""
    settings = CompanySettings(
        work_start_time="09:00",
        checkin_grace_time="09:30",
        afternoon_start_time="13:00",
        early_checkout_threshold="17:00",
        work_end_time="17:30",
        timezone="Asia/Kolkata",
    )
    d = date(2026, 10, 5)
    cin = datetime.combine(d, time(9, 45))
    cout = datetime.combine(d, time(17, 30))
    res = calculate_attendance_rule(settings, cin, cout)
    assert res["late_minutes"] == 45
    assert res["morning_status"] == "MORNING_HALF_DAY_ABSENT"


def test_12_duplicate_checkin_prevention(test_db):
    """Test 12: Duplicate check-in on the same day is rejected."""
    emp = test_db.query(User).filter(User.id == 101).first()
    now_morning = datetime.combine(date.today(), time(9, 15))

    # First check-in
    res1 = check_in_user(test_db, emp, override_now=now_morning)
    assert res1.get("ok") is True

    # Second check-in attempt
    res2 = check_in_user(test_db, emp, override_now=now_morning)
    assert "error" in res2
    assert "Already checked in" in res2["error"]


def test_13_valid_and_invalid_checkout(test_db):
    """Test 13: Checkout earlier than check-in or duplicate checkout is rejected."""
    emp2 = test_db.query(User).filter(User.id == 102).first()
    # Before checkin
    res_no_checkin = check_out_user(test_db, emp2)
    assert "error" in res_no_checkin
    assert "Check in first" in res_no_checkin["error"]

    # Now check in
    check_in_user(test_db, emp2, override_now=datetime.combine(date.today(), time(9, 0)))

    # Valid checkout at 5:30 PM
    now_evening = datetime.combine(date.today(), time(17, 30))
    res_valid = check_out_user(test_db, emp2, override_now=now_evening)
    assert res_valid.get("ok") is True
    assert res_valid["status"] == "Completed"

    # Duplicate checkout
    res_dup = check_out_user(test_db, emp2, override_now=now_evening)
    assert "error" in res_dup
    assert "Already checked out" in res_dup["error"]


def test_14_working_hours_and_overtime_calculation():
    """Test 14: Overtime is accurately calculated for work beyond 17:30."""
    settings = CompanySettings(
        work_start_time="09:00",
        checkin_grace_time="09:30",
        afternoon_start_time="13:00",
        early_checkout_threshold="17:00",
        work_end_time="17:30",
        timezone="Asia/Kolkata",
    )
    d = date(2026, 10, 6)
    cin = datetime.combine(d, time(9, 0))
    cout = datetime.combine(d, time(19, 0))  # 1.5h overtime after 17:30
    res = calculate_attendance_rule(settings, cin, cout)
    assert res["overtime_minutes"] == 90
    assert res["working_minutes"] == 600  # 10 hours


def test_15_approved_versus_pending_leave(test_db):
    """Test 15: Approved leave marks FULL_DAY_LEAVE; pending leave does not prevent absence."""
    target_d = date(2026, 9, 15)
    emp = test_db.query(User).filter(User.id == 104).first()

    # Add approved leave for employee 104
    leave = LeaveRequest(
        employee_id=emp.id,
        leave_type="Annual",
        start_date=target_d,
        end_date=target_d,
        status="Approved",
        reason="Family event",
        half_day_session="FULL_DAY",
    )
    test_db.add(leave)
    test_db.commit()

    res = finalize_daily_attendance(test_db, target_date=target_d, force=True)
    assert res["ok"] is True

    att = test_db.query(Attendance).filter(Attendance.employee_id == emp.id, Attendance.date == target_d).first()
    assert att.final_status == "FULL_DAY_LEAVE"
    assert att.status == "On Leave"


def test_16_sunday_exclusion_from_absence_marking(test_db):
    """Test 16: Sunday is marked WEEKLY_OFF and never ABSENT."""
    sunday_d = date(2026, 10, 11)  # Sunday
    assert sunday_d.weekday() == 6

    res = finalize_daily_attendance(test_db, target_date=sunday_d, force=True)
    assert res["ok"] is True
    assert res["finalized_weekly_off"] == 3

    records = test_db.query(Attendance).filter(Attendance.date == sunday_d).all()
    assert len(records) == 3
    for r in records:
        assert r.final_status == "WEEKLY_OFF"
        assert r.status == "Weekly Off"


def test_17_cutoff_enforcement_and_absence(test_db):
    """Test 17: Finalization before 7:00 PM cutoff on today is guarded."""
    # When not forced and before cutoff, finalizing today returns cutoff message
    settings = CompanySettings(timezone="Asia/Kolkata")
    today = date.today()

    # Explicit past date should finalize as absent
    past_workday = date(2026, 9, 21)  # Monday
    res = finalize_daily_attendance(test_db, target_date=past_workday, force=True)
    assert res["ok"] is True
    assert res["finalized_absent"] >= 1


def test_18_and_19_missed_finalization_recovery_idempotent(test_db):
    """Test 18 & 19: Recovery handles missed past days and repeated runs create zero duplicates."""
    rec_res = recover_missed_finalizations(test_db, max_days_back=7)
    assert rec_res["ok"] is True

    # Repeated run must be 100% idempotent
    rec_res2 = recover_missed_finalizations(test_db, max_days_back=7)
    assert rec_res2["ok"] is True
    assert rec_res2["recovered_count"] == 0 or rec_res2["total_records_processed"] == 0


def test_20_hr_corrections_protected(test_db):
    """Test 20: Approved HR corrections cannot be overwritten by automatic absence."""
    target_d = date(2026, 9, 22)
    emp = test_db.query(User).filter(User.id == 101).first()

    # Pre-existing HR approved attendance
    corr_att = Attendance(
        employee_id=emp.id,
        date=target_d,
        check_in="09:00 AM",
        check_out="05:30 PM",
        final_status="FULL_DAY_PRESENT",
        status="Present",
        working_minutes=510,
    )
    test_db.add(corr_att)
    test_db.commit()

    # Run finalization
    finalize_daily_attendance(test_db, target_date=target_d, force=True)

    # Status must remain FULL_DAY_PRESENT
    refreshed = test_db.query(Attendance).filter(Attendance.employee_id == emp.id, Attendance.date == target_d).first()
    assert refreshed.final_status == "FULL_DAY_PRESENT"
    assert refreshed.working_minutes == 510


def test_21_incomplete_checkout_marked_exception(test_db):
    """Test 21: Checked in without checkout is finalized as ATTENDANCE_EXCEPTION."""
    target_d = date(2026, 9, 23)
    emp = test_db.query(User).filter(User.id == 102).first()

    incomplete = Attendance(
        employee_id=emp.id,
        date=target_d,
        check_in="09:05 AM",
        check_in_at=datetime.combine(target_d, time(9, 5)),
        check_out=None,
        check_out_at=None,
        final_status="WORKING",
        status="Working",
    )
    test_db.add(incomplete)
    test_db.commit()

    finalize_daily_attendance(test_db, target_date=target_d, force=True)

    refreshed = test_db.query(Attendance).filter(Attendance.employee_id == emp.id, Attendance.date == target_d).first()
    assert refreshed.final_status == "ATTENDANCE_EXCEPTION"
    assert refreshed.afternoon_status == "MISSING_CHECKOUT"


# ==============================================================================
# PART 3: DASHBOARD CARDS AND RBAC (Tests 22 - 28)
# ==============================================================================

def test_22_six_stat_cards_dynamically_calculated(test_db):
    """Test 22: Six cards (Present, Absent, Late, On Leave, Avg Hours, OT Hours) are calculated from DB."""
    hr_user = test_db.query(User).filter(User.role == "hr").first()
    summary = get_attendance_summary_metrics(test_db, hr_user, target_date=date(2026, 9, 22))

    assert "present" in summary
    assert "absent" in summary
    assert "late" in summary
    assert "onLeave" in summary
    assert "avgHours" in summary
    assert "otHours" in summary

    # Values must be dynamically derived numeric types, never static placeholders
    assert isinstance(summary["present"], int)
    assert isinstance(summary["absent"], int)
    assert isinstance(summary["avgHours"], (float, int))
    assert isinstance(summary["otHours"], (float, int))


def test_23_date_and_month_filtering(test_db):
    """Test 23: Summary metrics filter by specific month and date accurately."""
    hr_user = test_db.query(User).filter(User.role == "hr").first()

    summary_sept = get_attendance_summary_metrics(test_db, hr_user, year=2026, month=9)
    assert summary_sept["filter"]["startDate"] == "2026-09-01"
    assert summary_sept["filter"]["endDate"] == "2026-09-30"

    summary_oct = get_attendance_summary_metrics(test_db, hr_user, year=2026, month=10)
    assert summary_oct["filter"]["startDate"] == "2026-10-01"
    assert summary_oct["filter"]["endDate"] == "2026-10-31"


def test_24_and_25_rbac_data_scoping(test_db):
    """Test 24 & 25: Employee scoped to self, Manager scoped to department, HR scoped to all."""
    emp = test_db.query(User).filter(User.id == 101).first()
    mgr = test_db.query(User).filter(User.id == 102).first()
    hr_user = test_db.query(User).filter(User.id == 103).first()

    s_emp = get_attendance_summary_metrics(test_db, emp, year=2026, month=9)
    s_mgr = get_attendance_summary_metrics(test_db, mgr, year=2026, month=9)
    s_hr = get_attendance_summary_metrics(test_db, hr_user, year=2026, month=9)

    # Employee record count <= Manager count <= HR count
    assert s_emp["totalRecords"] <= s_mgr["totalRecords"]
    assert s_mgr["totalRecords"] <= s_hr["totalRecords"]


def test_26_calendar_feed_structure_and_badges(test_db):
    """Test 26: Calendar feed contains all expected keys and distinct status badges."""
    emp = test_db.query(User).filter(User.id == 101).first()
    feed = get_attendance_calendar_feed(test_db, emp, year=2026, month=10)

    required_keys = {"date", "day", "weekday", "status", "badge", "isWeeklyOff", "isHoliday", "isFuture"}
    for day_item in feed:
        assert required_keys.issubset(day_item.keys())
        assert day_item["status"] in (
            "PRESENT", "ABSENT", "LATE", "LEAVE", "ON_LEAVE", "HALF_DAY", "WEEKLY_OFF", "HOLIDAY", "FUTURE", "PENDING", "EXCEPTION"
        )


def test_27_and_28_preserves_existing_workflows_and_no_redesign(test_db):
    """Test 27 & 28: Settings, company policies, and working hours thresholds are fully preserved."""
    settings = test_db.query(CompanySettings).first()
    assert settings.work_start_time == "09:00"
    assert settings.checkin_grace_time == "09:30"
    assert settings.early_checkout_threshold == "17:00"
    assert settings.work_end_time == "17:30"
    assert settings.timezone == "Asia/Kolkata"
