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
def isolation_db():
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
    seed_2026_holidays(db)
    seed_2027_holidays(db, force_active=True)

    # Users
    emp_a = User(
        name="Employee Alpha",
        email="emp_a@mindful.com",
        password_hash=hash_password("Pass@123"),
        role="employee",
        department="Engineering",
        employee_code="EMP_A",
    )
    emp_b = User(
        name="Employee Beta",
        email="emp_b@mindful.com",
        password_hash=hash_password("Pass@123"),
        role="employee",
        department="Engineering",
        employee_code="EMP_B",
    )
    emp_empty = User(
        name="Employee Empty",
        email="emp_empty@mindful.com",
        password_hash=hash_password("Pass@123"),
        role="employee",
        department="Design",
        employee_code="EMP_EMPTY",
    )
    mgr_eng = User(
        name="Manager Eng",
        email="mgr_eng@mindful.com",
        password_hash=hash_password("Pass@123"),
        role="manager",
        department="Engineering",
        employee_code="MGR_ENG",
    )
    hr_user = User(
        name="HR Admin",
        email="hr_admin@mindful.com",
        password_hash=hash_password("Pass@123"),
        role="hr",
        department="Human Resources",
        employee_code="HR_001",
    )
    db.add_all([emp_a, emp_b, emp_empty, mgr_eng, hr_user])
    db.commit()

    # Populate distinct attendance records
    d_oct5 = date(2026, 10, 5) # Monday
    att_a = Attendance(
        employee_id=emp_a.id,
        date=d_oct5,
        check_in="09:15 AM",
        check_out="05:15 PM",
        check_in_at=datetime.combine(d_oct5, time(9, 15)),
        check_out_at=datetime.combine(d_oct5, time(17, 15)),
        arrival_status="ON_TIME",
        attendance_day_value=1.0,
        working_minutes=480,
        late_minutes=0,
        overtime_minutes=0,
        final_status="FULL_DAY_PRESENT",
        status="Completed",
    )
    att_b = Attendance(
        employee_id=emp_b.id,
        date=d_oct5,
        check_in=None,
        check_out=None,
        arrival_status=None,
        attendance_day_value=0.0,
        working_minutes=0,
        late_minutes=0,
        overtime_minutes=0,
        final_status="ABSENT",
        status="Absent",
    )
    db.add_all([att_a, att_b])
    db.commit()

    yield db
    db.close()


def test_a_two_employees_have_different_records(isolation_db):
    """Test A: Two employees have distinct records; each sees only their own data."""
    emp_a = isolation_db.query(User).filter(User.email == "emp_a@mindful.com").first()
    emp_b = isolation_db.query(User).filter(User.email == "emp_b@mindful.com").first()

    # 1. Weekly history is employee-specific
    hist_a = get_user_attendance_history(isolation_db, emp_a)
    hist_b = get_user_attendance_history(isolation_db, emp_b)

    rec_a = next((w for w in hist_a["weekly"] if w["full_date"] == "2026-10-05"), None)
    rec_b = next((w for w in hist_b["weekly"] if w["full_date"] == "2026-10-05"), None)

    assert rec_a is not None and rec_a["status"] == "PRESENT"
    assert rec_b is not None and rec_b["status"] == "ABSENT"

    # 2. Calendar feed is employee-specific
    cal_a = get_attendance_calendar_feed(isolation_db, emp_a, 2026, 10)
    cal_b = get_attendance_calendar_feed(isolation_db, emp_b, 2026, 10)

    day_a = next(d for d in cal_a if d["date"] == "2026-10-05")
    day_b = next(d for d in cal_b if d["date"] == "2026-10-05")

    assert day_a["status"] == "PRESENT"
    assert day_b["status"] == "ABSENT"

    # 3. Summary cards differ according to actual records
    sum_a = get_attendance_summary_metrics(isolation_db, emp_a, target_date=date(2026, 10, 5))
    sum_b = get_attendance_summary_metrics(isolation_db, emp_b, target_date=date(2026, 10, 5))

    assert sum_a["present"] == 1
    assert sum_a["absent"] == 0
    assert sum_b["present"] == 0
    assert sum_b["absent"] == 1

    # 4. Employee A cannot access Employee B's private attendance by manipulating target_user_id
    cal_manipulated = get_attendance_calendar_feed(isolation_db, emp_a, 2026, 10, target_user_id=emp_b.id)
    manipulated_day = next(d for d in cal_manipulated if d["date"] == "2026-10-05")
    # Must still return emp_a's data (PRESENT), refusing cross-employee data leak
    assert manipulated_day["status"] == "PRESENT"


def test_b_employee_has_no_attendance(isolation_db):
    """Test B: Employee with no attendance records sees empty state and zeroed summary, not other users' records."""
    emp_empty = isolation_db.query(User).filter(User.email == "emp_empty@mindful.com").first()

    hist = get_user_attendance_history(isolation_db, emp_empty)
    assert hist["weekly"] == []

    summary = get_attendance_summary_metrics(isolation_db, emp_empty, target_date=date(2026, 10, 5))
    assert summary["present"] == 0
    assert summary["absent"] == 0
    assert summary["late"] == 0
    assert summary["onLeave"] == 0
    assert summary["avgHours"] == 0.0


def test_c_weekly_attendance_and_calendar_consistency(isolation_db):
    """Test C: Saved DB record, Weekly Attendance status, and Calendar status match 1:1."""
    emp_a = isolation_db.query(User).filter(User.email == "emp_a@mindful.com").first()
    hist_a = get_user_attendance_history(isolation_db, emp_a)
    cal_a = get_attendance_calendar_feed(isolation_db, emp_a, 2026, 10)
    cal_map = {c["date"]: c for c in cal_a}

    for row in hist_a["weekly"]:
        d_str = row["full_date"]
        if d_str in cal_map:
            c_day = cal_map[d_str]
            assert row["status"] == c_day["status"], f"Mismatch on {d_str}: weekly={row['status']} vs cal={c_day['status']}"
            assert row["canonical_status"] == c_day["canonical_status"]


def test_d_different_attendance_statuses(isolation_db):
    """Test D: Supports PRESENT, LATE, HALF_DAY, ABSENT, ON_LEAVE, HOLIDAY, WEEKLY_OFF consistently."""
    emp = isolation_db.query(User).filter(User.email == "emp_a@mindful.com").first()

    # 1. Weekly off Sunday
    sun_date = date(2026, 10, 4) # Sunday
    c_status, _, _ = get_canonical_attendance_status(None, is_weekly_off=True)
    assert c_status == "WEEKLY_OFF"

    # 2. Gandhi Jayanti Holiday
    h_date = date(2026, 10, 2)
    c_status_h, _, _ = get_canonical_attendance_status(None, is_holiday=True)
    assert c_status_h == "HOLIDAY"

    # 3. Approved Leave
    c_status_l, _, _ = get_canonical_attendance_status(None, has_leave=True)
    assert c_status_l == "ON_LEAVE"

    # 4. Half day late arrival
    settings = isolation_db.query(CompanySettings).first()
    t_in = datetime.combine(date(2026, 10, 6), time(9, 45))
    t_out = datetime.combine(date(2026, 10, 6), time(17, 15))
    rule = calculate_attendance_rule(settings, checkin_dt=t_in, checkout_dt=t_out)
    assert rule["arrival_status"] == "LATE"
    assert rule["attendance_day_value"] == 0.5
    assert rule["canonical_status"] == "HALF_DAY"


def test_e_different_dates_and_months(isolation_db):
    """Test E: Date and month filtering correctly fetches month-specific records without bleed."""
    emp_a = isolation_db.query(User).filter(User.email == "emp_a@mindful.com").first()
    cal_oct = get_attendance_calendar_feed(isolation_db, emp_a, 2026, 10)
    cal_nov = get_attendance_calendar_feed(isolation_db, emp_a, 2026, 11)

    assert len(cal_oct) == 31
    assert len(cal_nov) == 30
    assert all(d["date"].startswith("2026-10") for d in cal_oct)
    assert all(d["date"].startswith("2026-11") for d in cal_nov)


def test_f_role_based_access(isolation_db):
    """Test F: Employees see only self; Managers see only department; HR sees whole org."""
    emp_a = isolation_db.query(User).filter(User.email == "emp_a@mindful.com").first()
    emp_empty = isolation_db.query(User).filter(User.email == "emp_empty@mindful.com").first()
    mgr_eng = isolation_db.query(User).filter(User.email == "mgr_eng@mindful.com").first()
    hr_user = isolation_db.query(User).filter(User.email == "hr_admin@mindful.com").first()

    # Employee requesting another employee's summary gets scoped to self
    sum_emp_attempt = get_attendance_summary_metrics(isolation_db, emp_a, target_date=date(2026, 10, 5), target_user_id=emp_empty.id)
    assert sum_emp_attempt["present"] == 1 # scoped to emp_a, not emp_empty

    # Manager requesting own department member gets member's data
    sum_mgr_eng = get_attendance_summary_metrics(isolation_db, mgr_eng, target_date=date(2026, 10, 5), target_user_id=emp_a.id)
    assert sum_mgr_eng["present"] == 1

    # Manager requesting other department member (Design) is rejected back to self/team
    sum_mgr_other = get_attendance_summary_metrics(isolation_db, mgr_eng, target_date=date(2026, 10, 5), target_user_id=emp_empty.id)
    assert sum_mgr_other["filter"]["department"] in ("Engineering", "All")

    # HR requesting any employee gets that employee's exact summary
    sum_hr_target = get_attendance_summary_metrics(isolation_db, hr_user, target_date=date(2026, 10, 5), target_user_id=emp_a.id)
    assert sum_hr_target["present"] == 1


def test_g_updates_and_caching(isolation_db):
    """Test G: Dynamic attendance modifications update records without leaking across users."""
    emp_b = isolation_db.query(User).filter(User.email == "emp_b@mindful.com").first()
    d_oct7 = date(2026, 10, 7)

    # Check in emp_b on Oct 7
    att_new = Attendance(
        employee_id=emp_b.id,
        date=d_oct7,
        check_in="09:10 AM",
        check_out="05:20 PM",
        check_in_at=datetime.combine(d_oct7, time(9, 10)),
        check_out_at=datetime.combine(d_oct7, time(17, 20)),
        arrival_status="ON_TIME",
        attendance_day_value=1.0,
        working_minutes=490,
        final_status="FULL_DAY_PRESENT",
        status="Completed",
    )
    isolation_db.add(att_new)
    isolation_db.commit()

    # Verify emp_b has the record, and emp_a does NOT
    hist_b = get_user_attendance_history(isolation_db, emp_b)
    rec_b = next((w for w in hist_b["weekly"] if w["full_date"] == "2026-10-07"), None)
    assert rec_b is not None
    assert rec_b["status"] == "PRESENT"

    emp_a = isolation_db.query(User).filter(User.email == "emp_a@mindful.com").first()
    hist_a = get_user_attendance_history(isolation_db, emp_a)
    rec_a = next((w for w in hist_a["weekly"] if w["full_date"] == "2026-10-07"), None)
    assert rec_a is None # emp_a has no record on Oct 7
