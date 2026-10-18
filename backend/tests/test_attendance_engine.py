from __future__ import annotations
from datetime import datetime, date, time
from app.models import CompanySettings, LeaveRequest, PermissionRequest
from app.services.attendance_service import calculate_attendance_rule


def get_mock_settings():
    return CompanySettings(
        work_start_time="09:00",
        checkin_grace_time="09:30",
        afternoon_start_time="13:00",
        early_checkout_threshold="17:00",
        work_end_time="17:30",
        timezone="Asia/Kolkata",
    )


def test_case_1_ontime_checkin_and_official_end():
    # TEST 1: Check-in 09:00, Checkout 17:30
    settings = get_mock_settings()
    d = date(2026, 10, 1)
    cin = datetime.combine(d, time(9, 0))
    cout = datetime.combine(d, time(17, 30))

    res = calculate_attendance_rule(settings, cin, cout)
    assert res["morning_status"] == "PRESENT"
    assert res["afternoon_status"] == "PRESENT"
    assert res["final_status"] == "FULL_DAY_PRESENT"
    assert res["overtime_minutes"] == 0


def test_case_2_grace_period_checkin_and_early_threshold_checkout():
    # TEST 2: Check-in 09:30, Checkout 17:10
    settings = get_mock_settings()
    d = date(2026, 10, 1)
    cin = datetime.combine(d, time(9, 30))
    cout = datetime.combine(d, time(17, 10))

    res = calculate_attendance_rule(settings, cin, cout)
    assert res["morning_status"] == "PRESENT"
    assert res["afternoon_status"] == "PRESENT"
    assert res["final_status"] == "FULL_DAY_PRESENT"
    assert res["overtime_minutes"] == 0


def test_case_3_late_checkin_after_grace():
    # TEST 3: Check-in 09:31, Checkout 17:10
    settings = get_mock_settings()
    d = date(2026, 10, 1)
    cin = datetime.combine(d, time(9, 31))
    cout = datetime.combine(d, time(17, 10))

    res = calculate_attendance_rule(settings, cin, cout)
    assert res["morning_status"] == "MORNING_HALF_DAY_ABSENT"
    assert res["afternoon_status"] == "PRESENT"
    assert res["final_status"] == "MORNING_HALF_DAY_ABSENT"


def test_case_4_unauthorized_early_checkout():
    # TEST 4: Check-in 09:10, Checkout 16:30, No leave, No permission
    settings = get_mock_settings()
    d = date(2026, 10, 1)
    cin = datetime.combine(d, time(9, 10))
    cout = datetime.combine(d, time(16, 30))

    res = calculate_attendance_rule(settings, cin, cout)
    assert res["morning_status"] == "PRESENT"
    assert res["afternoon_status"] == "UNAUTHORIZED_EARLY_CHECKOUT"
    assert res["final_status"] == "ATTENDANCE_EXCEPTION"
    assert res["early_checkout_minutes"] == 30  # 17:00 - 16:30


def test_case_5_approved_permission_early_checkout():
    # TEST 5: Check-in 09:10, Checkout 16:30, Approved permission
    settings = get_mock_settings()
    d = date(2026, 10, 1)
    cin = datetime.combine(d, time(9, 10))
    cout = datetime.combine(d, time(16, 30))
    perm = PermissionRequest(
        employee_id=1,
        date=d,
        requested_checkout_time="04:30 PM",
        status="Approved",
    )

    res = calculate_attendance_rule(settings, cin, cout, approved_permission=perm)
    assert res["morning_status"] == "PRESENT"
    assert res["afternoon_status"] == "APPROVED_PERMISSION"
    assert res["final_status"] == "PRESENT_WITH_APPROVED_PERMISSION"


def test_case_6_approved_full_day_leave():
    # TEST 6: Approved full-day leave
    settings = get_mock_settings()
    leave = LeaveRequest(
        employee_id=1,
        half_day_session="FULL_DAY",
        status="Approved",
    )

    res = calculate_attendance_rule(settings, None, None, approved_leave=leave)
    assert res["morning_status"] == "APPROVED_LEAVE"
    assert res["afternoon_status"] == "APPROVED_LEAVE"
    assert res["final_status"] == "FULL_DAY_LEAVE"


def test_case_7_approved_morning_half_day_leave():
    # TEST 7: Approved morning half-day leave, afternoon attendance
    settings = get_mock_settings()
    d = date(2026, 10, 1)
    cin = datetime.combine(d, time(13, 0))  # check in at afternoon
    cout = datetime.combine(d, time(17, 30))
    leave = LeaveRequest(
        employee_id=1,
        half_day_session="MORNING_HALF_DAY",
        status="Approved",
    )

    res = calculate_attendance_rule(settings, cin, cout, approved_leave=leave)
    assert res["morning_status"] == "APPROVED_MORNING_LEAVE"
    assert res["afternoon_status"] == "PRESENT"
    assert res["final_status"] == "HALF_DAY_LEAVE"


def test_case_8_overtime_calculation():
    # TEST 8: Check-in 09:10, Checkout 18:20
    settings = get_mock_settings()
    d = date(2026, 10, 1)
    cin = datetime.combine(d, time(9, 10))
    cout = datetime.combine(d, time(18, 20))

    res = calculate_attendance_rule(settings, cin, cout)
    assert res["morning_status"] == "PRESENT"
    assert res["afternoon_status"] == "PRESENT"
    assert res["final_status"] == "FULL_DAY_PRESENT"
    assert res["overtime_minutes"] == 50  # 18:20 - 17:30 = 50 mins


def test_case_9_no_checkin_finalization():
    # TEST 9: No check-in, no leave
    settings = get_mock_settings()
    res = calculate_attendance_rule(settings, None, None)
    assert res["morning_status"] == "ABSENT"
    assert res["afternoon_status"] == "ABSENT"
    assert res["final_status"] == "ABSENT"


def test_case_10_incomplete_attendance():
    # TEST 10: Check-in but no checkout
    settings = get_mock_settings()
    d = date(2026, 10, 1)
    cin = datetime.combine(d, time(9, 15))

    res = calculate_attendance_rule(settings, cin, None)
    assert res["morning_status"] == "PRESENT"
    assert res["afternoon_status"] == "PENDING"
    assert res["final_status"] == "INCOMPLETE"
