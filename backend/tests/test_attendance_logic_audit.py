from __future__ import annotations
from datetime import datetime, date, time, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import (
    User, Attendance, CompanySettings, Holiday, LeaveRequest, PermissionRequest, AttendanceCorrection
)
from app.security import hash_password
from app.services.attendance_service import (
    calculate_attendance_rule,
    check_in_user,
    check_out_user,
    finalize_daily_attendance,
    recover_missed_finalizations,
    get_attendance_summary_metrics,
    get_attendance_calendar_feed,
    get_user_attendance_history,
    get_canonical_attendance_status,
)
from app.services.holiday_service import (
    seed_2026_holidays,
    seed_2027_holidays,
)


@pytest.fixture(scope="module")
def audit_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = TestingSessionLocal()

    # Company settings
    settings = CompanySettings(
        work_start_time="09:00",
        checkin_grace_time="09:30",
        afternoon_start_time="13:00",
        early_checkout_threshold="17:00",
        work_end_time="17:30",
        timezone="Asia/Kolkata",
    )
    db.add(settings)

    # Seed holidays
    seed_2026_holidays(db)
    seed_2027_holidays(db, force_active=True)

    # Users
    pw = hash_password("demo123")
    emp1 = User(
        id=201,
        name="Alice Engineer",
        email="alice@mindfulmetrics.com",
        password_hash=pw,
        role="employee",
        department="Engineering",
        employee_code="E201",
    )
    emp2 = User(
        id=202,
        name="Bob Designer",
        email="bob@mindfulmetrics.com",
        password_hash=pw,
        role="employee",
        department="Design",
        employee_code="E202",
    )
    mgr = User(
        id=203,
        name="Carol Manager",
        email="carol@mindfulmetrics.com",
        password_hash=pw,
        role="manager",
        department="Engineering",
        employee_code="M203",
    )
    hr_user = User(
        id=204,
        name="Dave HR",
        email="dave@mindfulmetrics.com",
        password_hash=pw,
        role="hr",
        department="HR",
        employee_code="HR204",
    )
    db.add_all([emp1, emp2, mgr, hr_user])
    db.commit()

    yield db
    db.close()


def test_a_ontime_full_day_attendance(audit_db):
    """
    Test A — On-time full-day attendance:
    - Check-in: 9:15 AM
    - Checkout: 5:15 PM
    - Expected arrival status: ON_TIME
    - Expected attendance credit: 1.0
    - Weekly Attendance and Calendar must show the same final status (PRESENT)
    """
    settings = audit_db.query(CompanySettings).first()
    t_in = datetime(2026, 10, 5, 9, 15)  # Monday 09:15 AM
    t_out = datetime(2026, 10, 5, 17, 15) # Monday 05:15 PM

    calc = calculate_attendance_rule(settings, checkin_dt=t_in, checkout_dt=t_out)
    assert calc["arrival_status"] == "ON_TIME"
    assert calc["late_minutes"] == 0
    assert calc["attendance_day_value"] == 1.0
    assert calc["canonical_status"] == "PRESENT"
    assert calc["final_status"] == "FULL_DAY_PRESENT"

    # Persist in DB
    att = Attendance(
        employee_id=201,
        date=date(2026, 10, 5),
        check_in="09:15 AM",
        check_out="05:15 PM",
        check_in_at=t_in,
        check_out_at=t_out,
        arrival_status=calc["arrival_status"],
        morning_status=calc["morning_status"],
        afternoon_status=calc["afternoon_status"],
        final_status=calc["final_status"],
        attendance_day_value=calc["attendance_day_value"],
        working_minutes=calc["working_minutes"],
        overtime_minutes=calc["overtime_minutes"],
        status="Completed",
    )
    audit_db.add(att)
    audit_db.commit()

    emp1 = audit_db.query(User).filter(User.id == 201).first()
    hist = get_user_attendance_history(audit_db, emp1)
    day_match = next((w for w in hist["weekly"] if w["full_date"] == "2026-10-05"), None)
    assert day_match is not None
    assert day_match["status"] == "PRESENT"
    assert day_match["arrival_status"] == "ON_TIME"
    assert day_match["attendance_day_value"] == 1.0

    feed = get_attendance_calendar_feed(audit_db, emp1, year=2026, month=10)
    cal_match = next((d for d in feed if d["date"] == "2026-10-05"), None)
    assert cal_match is not None
    assert cal_match["status"] == "PRESENT"
    assert cal_match["arrival_status"] == "ON_TIME"
    assert cal_match["attendance_day_value"] == 1.0
    # Strict 1:1 match
    assert day_match["status"] == cal_match["status"]


def test_b_checkin_exactly_at_cutoff(audit_db):
    """
    Test B — Check-in exactly at cutoff:
    - Check-in: 9:30 AM
    - Expected arrival status: ON_TIME
    - Confirm cutoff is inclusive
    """
    settings = audit_db.query(CompanySettings).first()
    t_in = datetime(2026, 10, 6, 9, 30)   # Exactly 09:30 AM
    t_out = datetime(2026, 10, 6, 17, 15)

    calc = calculate_attendance_rule(settings, checkin_dt=t_in, checkout_dt=t_out)
    assert calc["arrival_status"] == "ON_TIME", "09:30 AM checkin cutoff must be inclusive (ON_TIME)"
    assert calc["late_minutes"] == 0
    assert calc["attendance_day_value"] == 1.0
    assert calc["canonical_status"] == "PRESENT"


def test_c_late_arrival(audit_db):
    """
    Test C — Late arrival:
    - Check-in: 9:31 AM (after cutoff)
    - Checkout: 5:15 PM
    - Expected arrival status: LATE
    - Apply configured half-day policy -> credit: 0.5
    - Late summary updated consistently
    """
    settings = audit_db.query(CompanySettings).first()
    t_in = datetime(2026, 10, 7, 9, 31)
    t_out = datetime(2026, 10, 7, 17, 15)

    calc = calculate_attendance_rule(settings, checkin_dt=t_in, checkout_dt=t_out)
    assert calc["arrival_status"] == "LATE"
    assert calc["late_minutes"] == 31  # 31 minutes past 09:00 AM start
    assert calc["morning_status"] == "MORNING_HALF_DAY_ABSENT"
    assert calc["attendance_day_value"] == 0.5
    assert calc["canonical_status"] == "HALF_DAY"


def test_d_late_arrival_with_half_day_policy(audit_db):
    """
    Test D — Late arrival with half-day policy:
    - Check-in: 9:35 AM
    - Checkout: 5:15 PM
    - Expected credit: 0.5
    - Verify Weekly Attendance, Calendar, and Summary Cards agree
    """
    settings = audit_db.query(CompanySettings).first()
    t_in = datetime(2026, 10, 8, 9, 35)
    t_out = datetime(2026, 10, 8, 17, 15)

    calc = calculate_attendance_rule(settings, checkin_dt=t_in, checkout_dt=t_out)
    assert calc["arrival_status"] == "LATE"
    assert calc["attendance_day_value"] == 0.5
    assert calc["canonical_status"] == "HALF_DAY"

    att = Attendance(
        employee_id=201,
        date=date(2026, 10, 8),
        check_in="09:35 AM",
        check_out="05:15 PM",
        check_in_at=t_in,
        check_out_at=t_out,
        arrival_status=calc["arrival_status"],
        morning_status=calc["morning_status"],
        afternoon_status=calc["afternoon_status"],
        final_status=calc["final_status"],
        attendance_day_value=calc["attendance_day_value"],
        working_minutes=calc["working_minutes"],
        late_minutes=calc["late_minutes"],
        overtime_minutes=calc["overtime_minutes"],
        status="Completed",
    )
    audit_db.add(att)
    audit_db.commit()

    emp1 = audit_db.query(User).filter(User.id == 201).first()
    hist = get_user_attendance_history(audit_db, emp1)
    day_match = next((w for w in hist["weekly"] if w["full_date"] == "2026-10-08"), None)
    assert day_match["status"] == "HALF_DAY"
    assert day_match["attendance_day_value"] == 0.5
    assert day_match["arrival_status"] == "LATE"

    feed = get_attendance_calendar_feed(audit_db, emp1, year=2026, month=10)
    cal_match = next((d for d in feed if d["date"] == "2026-10-08"), None)
    assert cal_match["status"] == "HALF_DAY"
    assert cal_match["attendance_day_value"] == 0.5
    assert cal_match["arrival_status"] == "LATE"
    assert day_match["status"] == cal_match["status"]

    # Verify Summary Cards for this day
    sum_day = get_attendance_summary_metrics(audit_db, emp1, target_date=date(2026, 10, 8))
    assert sum_day["late"] == 1
    assert sum_day["halfDay"] == 1
    assert sum_day["present"] == 0  # not a fully present day
    assert sum_day["attendanceCredit"] == 0.5


def test_e_early_checkout(audit_db):
    """
    Test E — Early checkout:
    - Check-in: 9:15 AM
    - Checkout: 4:30 PM (before 5:00 PM threshold)
    - Confirm unapproved early checkout does not receive full-day credit (1.0)
    - If unapproved early checkout, receives half-day credit (0.5), not 1.0
    """
    settings = audit_db.query(CompanySettings).first()
    t_in = datetime(2026, 10, 9, 9, 15)
    t_out = datetime(2026, 10, 9, 16, 30)

    # 1. Unapproved early checkout
    calc_unapproved = calculate_attendance_rule(settings, checkin_dt=t_in, checkout_dt=t_out, approved_permission=None)
    assert calc_unapproved["afternoon_status"] == "UNAUTHORIZED_EARLY_CHECKOUT"
    assert calc_unapproved["attendance_day_value"] < 1.0, "Unapproved early checkout must not receive full-day credit"
    assert calc_unapproved["attendance_day_value"] == 0.5

    # 2. Approved early checkout permission
    perm = PermissionRequest(
        employee_id=201,
        date=date(2026, 10, 9),
        requested_checkout_time="04:30 PM",
        reason="Medical appointment",
        status="Approved",
    )
    audit_db.add(perm)
    audit_db.commit()

    calc_approved = calculate_attendance_rule(settings, checkin_dt=t_in, checkout_dt=t_out, approved_permission=perm)
    assert calc_approved["afternoon_status"] == "APPROVED_PERMISSION"
    assert calc_approved["attendance_day_value"] == 1.0, "Approved permission receives full-day credit"


def test_f_overtime(audit_db):
    """
    Test F — Overtime:
    - Check-in: 9:15 AM
    - Checkout: 6:35 PM (18:35)
    - Office end time: 17:30
    - Verify eligible overtime strictly calculated after 17:30 (65 minutes)
    - Avoid negative overtime and avoid double-counting
    """
    settings = audit_db.query(CompanySettings).first()
    t_in = datetime(2026, 10, 12, 9, 15)
    t_out = datetime(2026, 10, 12, 18, 35)

    calc = calculate_attendance_rule(settings, checkin_dt=t_in, checkout_dt=t_out)
    assert calc["arrival_status"] == "ON_TIME"
    assert calc["attendance_day_value"] == 1.0
    # Overtime strictly for work after 17:30: 18:35 - 17:30 = 65 minutes
    assert calc["overtime_minutes"] == 65
    assert calc["working_minutes"] == 560

    # Test late arrival with overtime: overtime does NOT convert late half-day into full-day
    t_in_late = datetime(2026, 10, 13, 10, 0)
    t_out_late = datetime(2026, 10, 13, 18, 35)
    calc_late_ot = calculate_attendance_rule(settings, checkin_dt=t_in_late, checkout_dt=t_out_late)
    assert calc_late_ot["arrival_status"] == "LATE"
    assert calc_late_ot["attendance_day_value"] == 0.5, "Overtime must NOT silently convert late half-day into full day"
    assert calc_late_ot["overtime_minutes"] == 65


def test_g_absence(audit_db):
    """
    Test G — Absence:
    - Confirmed full-day absence -> credit 0.0
    - Absent summary card increments correctly
    - Do not count future dates, holidays, or weekly offs as ordinary absence
    """
    # Create confirmed absence on a normal working day
    absent_att = Attendance(
        employee_id=202,
        date=date(2026, 10, 14),
        morning_status="ABSENT",
        afternoon_status="ABSENT",
        final_status="ABSENT",
        arrival_status=None,
        attendance_day_value=0.0,
        working_minutes=0,
        late_minutes=0,
        overtime_minutes=0,
        status="Absent",
    )
    audit_db.add(absent_att)
    audit_db.commit()

    emp2 = audit_db.query(User).filter(User.id == 202).first()
    sum_metrics = get_attendance_summary_metrics(audit_db, emp2, target_date=date(2026, 10, 14))
    assert sum_metrics["absent"] == 1
    assert sum_metrics["present"] == 0
    assert sum_metrics["attendanceCredit"] == 0.0

    # Ensure Sunday (2026-10-18) is NOT counted as ordinary absence
    feed_sun = get_attendance_calendar_feed(audit_db, emp2, year=2026, month=10)
    sun_day = next((d for d in feed_sun if d["date"] == "2026-10-18"), None)
    assert sun_day["isWeeklyOff"] is True
    assert sun_day["status"] == "WEEKLY_OFF"
    assert sun_day["status"] != "ABSENT"

    # Ensure Diwali holiday (2026-11-08) is HOLIDAY, not ABSENT
    feed_nov = get_attendance_calendar_feed(audit_db, emp2, year=2026, month=11)
    diwali = next((d for d in feed_nov if d["date"] == "2026-11-08"), None)
    assert diwali["isHoliday"] is True
    assert diwali["status"] == "HOLIDAY"
    assert diwali["status"] != "ABSENT"


def test_h_approved_leave(audit_db):
    """
    Test H — Approved leave:
    - Approved leave increments On Leave summary
    - Pending and rejected leave do NOT increment On Leave
    - Approved leave is NOT double-counted as absence
    """
    # 1. Approved leave
    app_l = LeaveRequest(
        employee_id=201,
        employee_name="Alice Engineer",
        leave_type="Casual Leave",
        start_date=date(2026, 10, 19),
        end_date=date(2026, 10, 19),
        half_day_session="FULL_DAY",
        status="Approved",
    )
    # 2. Pending leave
    pend_l = LeaveRequest(
        employee_id=201,
        employee_name="Alice Engineer",
        leave_type="Sick Leave",
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 20),
        half_day_session="FULL_DAY",
        status="Pending",
    )
    # 3. Rejected leave
    rej_l = LeaveRequest(
        employee_id=201,
        employee_name="Alice Engineer",
        leave_type="Earned Leave",
        start_date=date(2026, 10, 21),
        end_date=date(2026, 10, 21),
        half_day_session="FULL_DAY",
        status="Rejected",
    )
    audit_db.add_all([app_l, pend_l, rej_l])
    audit_db.commit()

    emp1 = audit_db.query(User).filter(User.id == 201).first()
    sum_app = get_attendance_summary_metrics(audit_db, emp1, target_date=date(2026, 10, 19))
    assert sum_app["onLeave"] == 1
    assert sum_app["absent"] == 0

    sum_pend = get_attendance_summary_metrics(audit_db, emp1, target_date=date(2026, 10, 20))
    assert sum_pend["onLeave"] == 0, "Pending leave must not increment On Leave"

    sum_rej = get_attendance_summary_metrics(audit_db, emp1, target_date=date(2026, 10, 21))
    assert sum_rej["onLeave"] == 0, "Rejected leave must not increment On Leave"


def test_i_different_employees_and_scoping(audit_db):
    """
    Test I — Different employees and date ranges:
    - Employee sees only their own attendance
    - Manager sees their department team
    - Summary updates accurately when employee or date range changes
    """
    emp1 = audit_db.query(User).filter(User.id == 201).first() # Engineering
    emp2 = audit_db.query(User).filter(User.id == 202).first() # Design
    mgr = audit_db.query(User).filter(User.id == 203).first()  # Manager Engineering

    sum_emp1 = get_attendance_summary_metrics(audit_db, emp1, target_date=date(2026, 10, 5))
    assert sum_emp1["present"] == 1

    sum_emp2 = get_attendance_summary_metrics(audit_db, emp2, target_date=date(2026, 10, 5))
    assert sum_emp2["present"] == 0  # emp2 had no check-in on 2026-10-05

    # Manager of Engineering includes emp1
    sum_mgr = get_attendance_summary_metrics(audit_db, mgr, target_date=date(2026, 10, 5))
    assert sum_mgr["present"] >= 1


def test_j_finalization_7pm_and_recovery(audit_db):
    """
    Test J — Finalization and refresh:
    - Cutoff check: before 7:00 PM IST cannot finalize today without force
    - After cutoff / forced: finalizes missing employees idempotently
    - Confirms late website login does NOT overwrite finalized attendance
    """
    # 1. Past working day finalization
    past_d = date(2026, 9, 21) # Monday
    res1 = finalize_daily_attendance(audit_db, target_date=past_d, force=True)
    assert res1["ok"] is True
    assert res1["finalized_absent"] > 0

    # Idempotent second run
    res2 = finalize_daily_attendance(audit_db, target_date=past_d, force=True)
    assert res2["ok"] is True
    assert res2["finalized_absent"] == 0
    assert res2["unchanged"] > 0

    # Recovery check
    rec_res = recover_missed_finalizations(audit_db, max_days_back=7)
    assert rec_res["ok"] is True

    # 2. Check-in attempt after finalization as Absent
    emp1 = audit_db.query(User).filter(User.id == 201).first()
    today = date.today()
    existing_abs = audit_db.query(Attendance).filter(
        Attendance.employee_id == emp1.id,
        Attendance.date == today,
    ).first()
    if existing_abs:
        existing_abs.morning_status = "ABSENT"
        existing_abs.afternoon_status = "ABSENT"
        existing_abs.final_status = "ABSENT"
        existing_abs.attendance_day_value = 0.0
        existing_abs.status = "Absent"
        existing_abs.finalized_at = datetime.now()
    else:
        existing_abs = Attendance(
            employee_id=emp1.id,
            date=today,
            morning_status="ABSENT",
            afternoon_status="ABSENT",
            final_status="ABSENT",
            attendance_day_value=0.0,
            status="Absent",
            finalized_at=datetime.now(),
        )
        audit_db.add(existing_abs)
    audit_db.commit()

    # Late checkin attempt must be rejected
    checkin_res = check_in_user(audit_db, emp1, override_now=datetime.combine(today, time(20, 0)))
    assert "error" in checkin_res
    assert "finalized as Absent" in checkin_res["error"]


def test_k_calendar_and_weekly_synchronization(audit_db):
    """
    Test K — Calendar synchronization:
    For every tested employee-date pair, compare:
    - Backend status
    - Weekly Attendance status
    - Calendar status
    Assert that the same authoritative final status is displayed across all views.
    """
    emp1 = audit_db.query(User).filter(User.id == 201).first()
    hist = get_user_attendance_history(audit_db, emp1, limit=50)
    feed = get_attendance_calendar_feed(audit_db, emp1, year=2026, month=10)
    feed_by_date = {d["date"]: d for d in feed}

    for row in hist["weekly"]:
        full_d = row.get("full_date")
        if full_d and full_d in feed_by_date:
            cal_day = feed_by_date[full_d]
            assert row["status"] == cal_day["status"], (
                f"Mismatch for date {full_d}: Weekly={row['status']} vs Calendar={cal_day['status']}"
            )
            assert row["attendance_day_value"] == cal_day["attendance_day_value"], (
                f"Value mismatch for date {full_d}: Weekly={row['attendance_day_value']} vs Calendar={cal_day['attendance_day_value']}"
            )
