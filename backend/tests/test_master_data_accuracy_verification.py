import pytest
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app, create_token, SessionLocal
from app.models import User, Attendance, Task, LeaveRequest, PermissionRequest, AttendanceCorrection, Prediction
from app.services.burnout_service import get_employee_core_metrics

client = TestClient(app)

@pytest.fixture(scope="module")
def db_ctx():
    db = SessionLocal()
    try:
        hr = db.query(User).filter(User.role == "hr").first()
        mgr = db.query(User).filter(User.role == "manager").first()
        employees = db.query(User).filter(User.role == "employee", User.department == mgr.department).all()
        all_employees = db.query(User).filter(User.role == "employee").all()
        yield {
            "db": db,
            "hr": hr,
            "mgr": mgr,
            "team_employees": employees,
            "all_employees": all_employees,
        }
    finally:
        db.close()

def test_1_different_employees_have_different_scores_and_no_universal_65_or_100(db_ctx):
    """Verify that employees with different records have different scores and no universal 65/100."""
    hr = db_ctx["hr"]
    headers = {"Authorization": f"Bearer {create_token(hr)}"}
    res = client.get("/api/hr/employees", headers=headers)
    assert res.status_code == 200
    emps = res.json()
    assert len(emps) >= 10

    # Ensure workload is not 65 for every employee
    workload_scores = [e["workload"] for e in emps if e["workload"] is not None]
    distinct_workloads = set(workload_scores)
    assert len(distinct_workloads) > 1, f"Expected variation in workloads, got {distinct_workloads}"
    assert not all(w == 65 for w in workload_scores), "Workload should not be universally 65"
    assert not all(w == 100 for w in workload_scores), "Workload should not be universally 100"

def test_2_cross_dashboard_consistency_for_same_employee(db_ctx):
    """Verify workload, burnout, and WLB match across Employee Dashboard, HR Detail, and Manager Detail."""
    db = db_ctx["db"]
    emp = db_ctx["team_employees"][0]
    mgr = db_ctx["mgr"]
    hr = db_ctx["hr"]

    emp_headers = {"Authorization": f"Bearer {create_token(emp)}"}
    mgr_headers = {"Authorization": f"Bearer {create_token(mgr)}"}
    hr_headers = {"Authorization": f"Bearer {create_token(hr)}"}

    # 1. Employee's own dashboard
    res_emp = client.get("/api/employee/dashboard", headers=emp_headers)
    assert res_emp.status_code == 200
    emp_kpis = res_emp.json()["kpis"]

    # 2. HR detail drawer
    res_hr = client.get(f"/api/users/{emp.id}/details", headers=hr_headers)
    assert res_hr.status_code == 200
    hr_data = res_hr.json()

    # 3. Manager detail drawer
    res_mgr = client.get(f"/api/manager/team/{emp.id}/details", headers=mgr_headers)
    assert res_mgr.status_code == 200
    mgr_data = res_mgr.json()

    # Assert exact score matches
    assert emp_kpis["workloadScore"] == hr_data["workload"]["workload_score"]
    assert hr_data["workload"]["workload_score"] == mgr_data["workload"]["workload_score"]

    assert emp_kpis["burnoutRisk"] == hr_data["wellbeing"]["burnout_score"]
    assert hr_data["wellbeing"]["burnout_score"] == mgr_data["wellbeing"]["burnout_score"]

    assert emp_kpis["wlbScore"] == hr_data["workload"]["work_life_balance_score"]
    assert hr_data["workload"]["work_life_balance_score"] == mgr_data["workload"]["work_life_balance_score"]

def test_3_detail_tab_counts_match_database(db_ctx):
    """Verify detail drawer tab counts match exact database record counts."""
    db = db_ctx["db"]
    emp = db_ctx["team_employees"][0]
    hr = db_ctx["hr"]
    headers = {"Authorization": f"Bearer {create_token(hr)}"}

    res = client.get(f"/api/users/{emp.id}/details", headers=headers)
    assert res.status_code == 200
    data = res.json()

    real_tasks_count = db.query(Task).filter(Task.employee_id == emp.id).count()
    real_leaves_count = db.query(LeaveRequest).filter(LeaveRequest.employee_id == emp.id).count()
    real_perms_count = db.query(PermissionRequest).filter(PermissionRequest.employee_id == emp.id).count()
    real_atts_count = db.query(Attendance).filter(Attendance.employee_id == emp.id).count()

    assert len(data["tasks"]) == real_tasks_count
    assert len(data["leaves"]) == real_leaves_count
    assert len(data["permissions"]) == real_perms_count
    assert len(data["attendance"]) == real_atts_count

def test_4_manager_trends_no_artificial_increments(db_ctx):
    """Verify trend graphs return actual observations without incremental +2 formulas."""
    mgr = db_ctx["mgr"]
    headers = {"Authorization": f"Bearer {create_token(mgr)}"}

    res = client.get("/api/manager/trends?days=7", headers=headers)
    assert res.status_code == 200
    data = res.json()

    b_trend = data["burnout_trend"]
    assert len(b_trend) == 7
    values = [p["value"] for p in b_trend]
    # Check that values are not artificially generated using an arithmetic progression (e.g. 52, 54, 56, 58...)
    diffs = [values[i+1] - values[i] for i in range(len(values)-1)]
    assert not (len(diffs) >= 4 and all(d == 2 for d in diffs)), "Trend data appears to be artificial +2 progression!"

def test_5_hr_attendance_counts_match_monitored_workforce(db_ctx):
    """Verify HR attendance dashboard counts only active monitored workforce (44 members)."""
    db = db_ctx["db"]
    hr = db_ctx["hr"]
    headers = {"Authorization": f"Bearer {create_token(hr)}"}

    today_str = date.today().isoformat()
    res = client.get(f"/api/attendance/all?date={today_str}", headers=headers)
    assert res.status_code == 200
    rows = res.json()

    # Monitored count must equal employees + managers (44), excluding HR user
    expected_monitored = db.query(User).filter(User.role.in_(["employee", "manager"])).count()
    assert len(rows) == expected_monitored
    assert all(r["role"] in ("employee", "manager") for r in rows)

def test_6_pending_corrections_reflects_actual_database_records(db_ctx):
    """Verify pending attendance corrections reflect actual database state."""
    db = db_ctx["db"]
    hr = db_ctx["hr"]
    headers = {"Authorization": f"Bearer {create_token(hr)}"}

    res = client.get("/api/attendance/correction/requests", headers=headers)
    assert res.status_code == 200
    corrections = res.json()

    db_pending = db.query(AttendanceCorrection).filter(AttendanceCorrection.status == "Pending").count()
    api_pending = sum(1 for c in corrections if c["status"] == "Pending")
    assert api_pending == db_pending
