from __future__ import annotations
import pytest
from datetime import date, datetime, time, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models import User, Attendance, LeaveRequest, Holiday, AttendanceCorrection, Prediction
from app.services.holiday_service import (
    SUPPLIED_2026_HOLIDAYS, seed_2026_holidays, is_holiday, is_weekly_off, SOURCE_NAME, SOURCE_REF
)
from app.services.attendance_service import (
    check_in_user, check_out_user, finalize_daily_attendance,
    create_attendance_correction_request, approve_attendance_correction, reject_attendance_correction
)
from app.services.burnout_service import predict_for_employee


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="module")
def auth_tokens(client):
    # Log in as HR, Manager, and Employee
    hr_res = client.post("/api/auth/login", json={"email": "hr@mindfulmetrics.com", "password": "demo123"})
    if hr_res.status_code != 200:
        hr_res = client.post("/api/auth/login", json={"email": "ajai@gmail.com", "password": "Ajai@123"})
    hr_token = hr_res.json()["token"]

    mgr_res = client.post("/api/auth/login", json={"email": "manager@mindfulmetrics.com", "password": "demo123"})
    if mgr_res.status_code != 200:
        mgr_res = client.post("/api/auth/login", json={"email": "aakas@gmail.com", "password": "Aakas@123"})
    mgr_token = mgr_res.json()["token"]

    emp_res = client.post("/api/auth/login", json={"email": "employee@mindfulmetrics.com", "password": "demo123"})
    if emp_res.status_code != 200:
        emp_res = client.post("/api/auth/login", json={"email": "vignesh@gmail.com", "password": "Vignesh@123"})
    emp_token = emp_res.json()["token"]

    return {"hr": hr_token, "mgr": mgr_token, "emp": emp_token}


# ==============================================================================
# SECTION A: 2026 TAMIL NADU GOVERNMENT PUBLIC HOLIDAYS & MIGRATION TESTS
# ==============================================================================

def test_all_24_supplied_holidays_present_in_postgres(db: Session):
    """Verify all 24 supplied 2026 Tamil Nadu public holidays exist with exact dates and names in PostgreSQL."""
    holidays = db.query(Holiday).filter(Holiday.calendar_year == 2026).all()
    assert len(holidays) == 24, f"Expected 24 holidays, found {len(holidays)}"

    h_dict = {h.holiday_name: h for h in holidays}
    for supp in SUPPLIED_2026_HOLIDAYS:
        name = supp["holiday_name"]
        assert name in h_dict, f"Missing holiday: {name}"
        record = h_dict[name]
        assert record.holiday_date == supp["holiday_date"], f"Date mismatch for {name}: {record.holiday_date} != {supp['holiday_date']}"
        assert isinstance(record.holiday_date, date), "Date must be stored as proper Date type"


def test_bank_annual_closing_applicability_is_bank_only(db: Session):
    """Verify that April 1 bank annual account-closing is marked 'bank_only'."""
    bank_h = db.query(Holiday).filter(Holiday.holiday_date == date(2026, 4, 1)).first()
    assert bank_h is not None
    assert bank_h.applicability == "bank_only"
    assert bank_h.holiday_type == "Bank Holiday"

    # General company employee should NOT consider this day a company holiday
    is_h_comp, _ = is_holiday(db, date(2026, 4, 1), calendar_type="company")
    assert is_h_comp is False, "Bank holiday must not be treated as a general company holiday"

    # Bank calendar DOES consider it a holiday
    is_h_bank, _ = is_holiday(db, date(2026, 4, 1), calendar_type="bank")
    assert is_h_bank is True


def test_holiday_seed_idempotency_no_duplicates(db: Session):
    """Verify re-running seed does not insert duplicates or delete records."""
    count_before = db.query(Holiday).filter(Holiday.calendar_year == 2026).count()
    res = seed_2026_holidays(db)
    count_after = db.query(Holiday).filter(Holiday.calendar_year == 2026).count()

    assert res["inserted"] == 0
    assert count_before == count_after == 24


def test_official_gazette_metadata_accuracy(db: Session):
    """Verify official source verification metadata."""
    sample = db.query(Holiday).filter(Holiday.calendar_year == 2026).first()
    assert sample.source_name == "Tamil Nadu Government Gazette Public Holidays 2026"
    assert "G.O.(Ms.) No. 708" in sample.source_reference
    assert sample.source_verified == 1


# ==============================================================================
# SECTION B: 7:00 PM ATTENDANCE FINALIZATION & 8:00 PM LOGIN BEHAVIOR
# ==============================================================================

def test_daily_attendance_finalization_marks_absent(db: Session):
    """Verify 7 PM finalization marks employees with no check-in as ABSENT on regular working days."""
    test_date = date(2026, 6, 10)  # Wednesday, normal working day, not a holiday
    is_h, _ = is_holiday(db, test_date)
    is_wo = is_weekly_off(test_date)
    assert not is_h and not is_wo, "Must be a regular working day"

    # Remove any existing attendance for test_date for clean testing
    db.query(Attendance).filter(Attendance.date == test_date).delete()
    db.commit()

    # Trigger finalization for test_date
    res = finalize_daily_attendance(db, target_date=test_date)
    assert res["ok"] is True
    assert res["finalized_absent"] > 0

    # Query attendance records
    atts = db.query(Attendance).filter(Attendance.date == test_date).all()
    assert len(atts) > 0
    for a in atts:
        assert a.final_status == "ABSENT"
        assert a.morning_status == "ABSENT"
        assert a.afternoon_status == "ABSENT"
        assert a.working_minutes == 0


def test_holiday_not_finalized_as_absent(db: Session):
    """Verify that an applicable Tamil Nadu Government holiday (e.g. May Day 2026-05-01) is not finalized as Absent."""
    holiday_date = date(2026, 5, 1)  # May Day (Friday)
    is_h, h_obj = is_holiday(db, holiday_date)
    assert is_h is True

    db.query(Attendance).filter(Attendance.date == holiday_date).delete()
    db.commit()

    res = finalize_daily_attendance(db, target_date=holiday_date)
    assert res["ok"] is True
    assert res["finalized_absent"] == 0
    assert res["finalized_holiday"] > 0

    atts = db.query(Attendance).filter(Attendance.date == holiday_date).all()
    for a in atts:
        assert a.final_status == "HOLIDAY"


def test_eight_pm_login_does_not_change_absent_attendance(client: TestClient, db: Session):
    """
    SECTION 9: Website login at 8:00 PM is NOT attendance check-in.
    Attendance must remain ABSENT.
    """
    emp = db.query(User).filter(User.role == "employee").first()
    assert emp is not None

    test_date = date(2026, 6, 17)  # Wednesday
    # Create finalized ABSENT record at 7 PM
    db.query(Attendance).filter(Attendance.employee_id == emp.id, Attendance.date == test_date).delete()
    absent_rec = Attendance(
        employee_id=emp.id,
        date=test_date,
        final_status="ABSENT",
        morning_status="ABSENT",
        afternoon_status="ABSENT",
        status="Absent",
        working_minutes=0,
    )
    db.add(absent_rec)
    db.commit()

    # Employee logs into website at 8:00 PM
    login_res = client.post("/api/auth/login", json={"email": emp.email, "password": "demo123"})
    if login_res.status_code != 200:
        login_res = client.post("/api/auth/login", json={"email": emp.email, "password": "Vignesh@123"})
    assert login_res.status_code == 200

    # Verify attendance record is STILL ABSENT
    db.refresh(absent_rec)
    assert absent_rec.final_status == "ABSENT", "Website login must NOT change finalized Absent attendance to Present!"
    assert absent_rec.check_in is None


def test_late_checkin_after_cutoff_is_blocked(db: Session):
    """Verify that late check-in attempt after 7 PM cutoff returns error and requires HR correction."""
    emp = db.query(User).filter(User.role == "employee").first()
    
    # Simulate check-in at 8:00 PM (20:00)
    fake_now = datetime(2026, 6, 17, 20, 0, 0)
    res = check_in_user(db, emp, override_now=fake_now)
    assert "error" in res
    assert "7:00 PM" in res["error"] or "correction" in res["error"].lower()


# ==============================================================================
# SECTION C: HR ATTENDANCE CORRECTION WORKFLOW & BURNOUT INTEGRATION
# ==============================================================================

def test_hr_attendance_correction_approval_workflow(db: Session):
    """
    Verify complete HR correction workflow:
    1. Employee submits correction request with date and reason.
    2. HR approves correction.
    3. Attendance status is updated to FULL_DAY_PRESENT.
    4. Live burnout risk prediction is triggered.
    """
    emp = db.query(User).filter(User.role == "employee").first()
    hr = db.query(User).filter(User.role == "hr").first()
    assert emp and hr

    target_date = date(2026, 5, 20)  # Wednesday
    # Clean previous records
    db.query(AttendanceCorrection).filter(AttendanceCorrection.employee_id == emp.id, AttendanceCorrection.attendance_date == target_date).delete()
    db.query(Attendance).filter(Attendance.employee_id == emp.id, Attendance.date == target_date).delete()
    
    # Initially Absent
    att = Attendance(
        employee_id=emp.id,
        date=target_date,
        final_status="ABSENT",
        status="Absent",
        working_minutes=0,
    )
    db.add(att)
    db.commit()

    # Step 1: Employee creates correction request
    req = create_attendance_correction_request(
        db,
        employee=emp,
        attendance_date=target_date,
        reason="Client site meeting in Chennai; missed logging in at 9:00 AM.",
        requested_check_in="09:00 AM",
        requested_check_out="05:30 PM",
    )
    assert req.get("ok") is True
    corr_id = req["id"]

    # Step 2: Unauthorized employee cannot approve
    unauth_res = approve_attendance_correction(db, approver=emp, correction_id=corr_id)
    assert "error" in unauth_res
    assert "Unauthorized" in unauth_res["error"]

    # Step 3: HR approves correction
    app_res = approve_attendance_correction(db, approver=hr, correction_id=corr_id)
    assert app_res.get("ok") is True
    assert app_res.get("new_status") == "FULL_DAY_PRESENT"

    # Step 4: Verify attendance record updated in DB
    db.refresh(att)
    assert att.final_status == "FULL_DAY_PRESENT"
    assert att.status == "Present"
    assert att.working_minutes == 510

    # Step 5: Verify burnout prediction was updated
    assert app_res.get("prediction") is not None
    assert "burnout_score" in app_res["prediction"]


def test_hr_attendance_correction_rejection_workflow(db: Session):
    """Verify that HR rejection preserves original attendance and records reason."""
    emp = db.query(User).filter(User.role == "employee").first()
    hr = db.query(User).filter(User.role == "hr").first()

    target_date = date(2026, 5, 21)
    req = create_attendance_correction_request(
        db,
        employee=emp,
        attendance_date=target_date,
        reason="Forgot to check in.",
    )
    corr_id = req["id"]

    rej_res = reject_attendance_correction(db, approver=hr, correction_id=corr_id, rejection_reason="No swipe record found.")
    assert rej_res.get("ok") is True
    assert rej_res.get("status") == "Rejected"

    corr = db.query(AttendanceCorrection).filter(AttendanceCorrection.id == corr_id).first()
    assert corr.status == "Rejected"
    assert corr.rejection_reason == "No swipe record found."


def test_holidays_api_endpoint(client: TestClient, auth_tokens):
    """Verify GET /api/holidays endpoint returns all 24 verified holidays."""
    res = client.get("/api/holidays", headers={"Authorization": f"Bearer {auth_tokens['emp']}"})
    assert res.status_code == 200
    holidays = res.json()
    assert len(holidays) == 24
    
    # Verify April 1 bank closing
    april1 = next((h for h in holidays if h["holiday_date"] == "2026-04-01"), None)
    assert april1 is not None
    assert april1["applicability"] == "bank_only"
    assert april1["source_verified"] is True
