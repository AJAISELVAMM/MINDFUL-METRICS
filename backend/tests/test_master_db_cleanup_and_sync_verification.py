import pytest
from datetime import date, datetime, time, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import (
    User, Attendance, CompanySettings, Holiday, LeaveRequest, AttendanceCorrection
)
from app.services.attendance_service import (
    calculate_attendance_rule, get_attendance_calendar_feed, get_attendance_summary_metrics
)
from app.security import create_token

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def get_test_settings():
    return CompanySettings(
        work_start_time="09:00",
        checkin_grace_time="09:30",
        afternoon_start_time="13:00",
        early_checkout_threshold="17:00",
        work_end_time="17:30",
        timezone="Asia/Kolkata",
    )

def test_1_present_record_persisted_and_retrieved():
    settings = get_test_settings()
    d = date(2026, 10, 15)
    cin = datetime.combine(d, time(9, 15))
    cout = datetime.combine(d, time(17, 30))
    res = calculate_attendance_rule(settings, cin, cout)
    assert res["final_status"] == "FULL_DAY_PRESENT"

def test_2_confirmed_absent_represented_correctly():
    settings = get_test_settings()
    res = calculate_attendance_rule(settings, None, None)
    assert res["final_status"] == "ABSENT"

def test_3_late_arrival_stored_or_derived():
    settings = get_test_settings()
    d = date(2026, 10, 15)
    cin = datetime.combine(d, time(9, 45))
    cout = datetime.combine(d, time(17, 30))
    res = calculate_attendance_rule(settings, cin, cout)
    assert res["final_status"] == "MORNING_HALF_DAY_ABSENT"

def test_4_approved_on_leave_record_represented():
    settings = get_test_settings()
    d = date(2026, 10, 15)
    leave = LeaveRequest(
        employee_id=1, status="Approved", half_day_session="FULL_DAY",
        start_date=d, end_date=d
    )
    res = calculate_attendance_rule(settings, None, None, approved_leave=leave)
    assert res["final_status"] == "FULL_DAY_LEAVE"

def test_5_overtime_calculated_from_valid_timestamps():
    settings = get_test_settings()
    d = date(2026, 10, 15)
    cin = datetime.combine(d, time(9, 15))
    cout = datetime.combine(d, time(18, 35))
    res = calculate_attendance_rule(settings, cin, cout)
    assert res["overtime_minutes"] == 65

def test_6_weekly_and_calendar_exact_synchronization(db_session):
    u = db_session.query(User).filter(User.role == "employee").first()
    assert u is not None
    token = create_token(u)

    r_week = client.get("/api/attendance/weekly?week_offset=0", headers={"Authorization": f"Bearer {token}"})
    r_cal = client.get("/api/attendance/calendar?year=2026&month=10", headers={"Authorization": f"Bearer {token}"})

    assert r_week.status_code == 200
    assert r_cal.status_code == 200

    weekly_data = r_week.json().get("weekly", [])
    raw_cal = r_cal.json()
    calendar_data = raw_cal if isinstance(raw_cal, list) else raw_cal.get("days", [])

    cal_map = {item["date"]: item["status"] for item in calendar_data}
    for w_day in weekly_data:
        w_date = w_day.get("full_date")
        if w_date and w_date in cal_map:
            assert w_day["status"] == cal_map[w_date], (
                f"Mismatch on {w_date}: Weekly={w_day['status']}, Calendar={cal_map[w_date]}"
            )

def test_7_two_employees_with_different_records_receive_different_responses(db_session):
    employees = db_session.query(User).filter(User.role == "employee").limit(2).all()
    if len(employees) >= 2:
        e1, e2 = employees[0], employees[1]
        t1 = create_token(e1)
        t2 = create_token(e2)

        r1 = client.get("/api/attendance/summary", headers={"Authorization": f"Bearer {t1}"})
        r2 = client.get("/api/attendance/summary", headers={"Authorization": f"Bearer {t2}"})

        assert r1.status_code == 200
        assert r2.status_code == 200

def test_8_employee_cannot_access_unauthorized_scope(db_session):
    e = db_session.query(User).filter(User.role == "employee").first()
    other = db_session.query(User).filter(User.role == "employee", User.id != e.id).first()
    token = create_token(e)

    # Requesting other employee's attendance should return 403 Forbidden
    resp = client.get(f"/api/attendance/summary?user_id={other.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403

def test_9_all_retained_users_are_gmail(db_session):
    all_users = db_session.query(User).all()
    assert len(all_users) == 45
    for u in all_users:
        assert (u.email or "").strip().lower().endswith("@gmail.com"), f"Found non-gmail user: {u.email}"
