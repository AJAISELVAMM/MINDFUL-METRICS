"""
Comprehensive System Verification using FastAPI TestClient to test all real database-backed endpoints.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_system():
    print("=" * 60, flush=True)
    print("MINDFUL METRICS - ALL ROLES & WORKFLOWS VERIFICATION", flush=True)
    print("=" * 60, flush=True)

    # 1. Health
    res = client.get("/api/health")
    assert res.status_code == 200
    print("[PASS] 1. Backend /api/health OK", flush=True)

    # 2. HR Login & Pages
    hr_login = client.post("/api/auth/login", json={"email": "ajai@gmail.com", "password": "Ajai@123"})
    assert hr_login.status_code == 200, f"HR login failed: {hr_login.text}"
    hr_token = hr_login.json()["token"]
    hr_headers = {"Authorization": f"Bearer {hr_token}"}
    print(f"[PASS] 2. HR Login OK: {hr_login.json()['user']['name']} (role={hr_login.json()['user']['role']})", flush=True)

    # HR Dashboard
    res = client.get("/api/hr/dashboard", headers=hr_headers)
    assert res.status_code == 200
    dash_kpis = res.json().get("kpis", {})
    print(f"[PASS] 3. HR Dashboard OK: Total Employees={dash_kpis.get('total_employees')}, Burnout={dash_kpis.get('burnout_rate')}%", flush=True)

    # HR Employees
    res = client.get("/api/hr/employees", headers=hr_headers)
    assert res.status_code == 200
    employees = res.json()
    assert len(employees) > 0
    print(f"[PASS] 4. HR Employees Directory OK: {len(employees)} employees", flush=True)

    # HR Attendance - Verify NO false HOLIDAY
    res = client.get("/api/hr/attendance?date=2026-10-22", headers=hr_headers)
    assert res.status_code == 200
    att_records = res.json() if isinstance(res.json(), list) else res.json().get("attendance", [])
    holiday_count = sum(1 for r in att_records if "holiday" in (r.get("status") or "").lower())
    print(f"[PASS] 5. HR Attendance OK: {len(att_records)} records, {holiday_count} false holidays on weekday (Expected 0)", flush=True)
    assert holiday_count == 0, "Attendance HOLIDAY bug still present!"

    # HR Leave
    res = client.get("/api/hr/leave", headers=hr_headers)
    assert res.status_code == 200
    print(f"[PASS] 6. HR Leave OK: {len(res.json())} leave requests", flush=True)

    # HR Tasks
    res = client.get("/api/tasks", headers=hr_headers)
    assert res.status_code == 200
    print(f"[PASS] 7. HR Tasks OK: {len(res.json())} tasks", flush=True)

    # HR Interventions
    res = client.get("/api/hr/interventions", headers=hr_headers)
    assert res.status_code == 200
    print(f"[PASS] 8. HR Interventions OK: {len(res.json())} interventions", flush=True)

    # 3. Employee Login & Pages
    emp_login = client.post("/api/auth/login", json={"email": "vignesh@gmail.com", "password": "Vignesh@123"})
    assert emp_login.status_code == 200
    emp_token = emp_login.json()["token"]
    emp_user = emp_login.json()["user"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}
    print(f"[PASS] 9. Employee Login OK: {emp_user['name']} (role={emp_user['role']})", flush=True)

    # Employee Dashboard
    res = client.get("/api/employee/dashboard", headers=emp_headers)
    assert res.status_code == 200
    emp_kpis = res.json().get("kpis", {})
    print(f"[PASS] 10. Employee Dashboard OK: Burnout Score={emp_kpis.get('burnout_score')}", flush=True)

    # Employee Profile Details
    res = client.get(f"/api/users/{emp_user['id']}/details", headers=emp_headers)
    assert res.status_code == 200
    det = res.json()
    assert det["profile"]["name"] == emp_user["name"]
    print(f"[PASS] 11. Employee Full Details OK: {det['profile']['name']} ({det['profile']['department']})", flush=True)

    # Employee Attendance Summary
    res = client.get("/api/attendance/summary", headers=emp_headers)
    assert res.status_code == 200
    print(f"[PASS] 12. Employee Attendance Summary OK", flush=True)

    # Employee Tasks
    res = client.get("/api/tasks", headers=emp_headers)
    assert res.status_code == 200
    print(f"[PASS] 13. Employee Tasks OK: {len(res.json())} tasks", flush=True)

    # Employee Trends
    res = client.get("/api/employee/trends", headers=emp_headers)
    assert res.status_code == 200
    print(f"[PASS] 14. Employee Trends OK: {len(res.json())} daily points", flush=True)

    # 4. Manager Login & Pages
    mgr_login = client.post("/api/auth/login", json={"email": "aakas@gmail.com", "password": "Aakas@123"})
    assert mgr_login.status_code == 200
    mgr_token = mgr_login.json()["token"]
    mgr_headers = {"Authorization": f"Bearer {mgr_token}"}
    print(f"[PASS] 15. Manager Login OK: {mgr_login.json()['user']['name']}", flush=True)

    res = client.get("/api/manager/dashboard", headers=mgr_headers)
    assert res.status_code == 200
    print(f"[PASS] 16. Manager Dashboard OK", flush=True)

    res = client.get("/api/manager/team", headers=mgr_headers)
    assert res.status_code == 200
    print(f"[PASS] 17. Manager Team OK: {len(res.json())} team members", flush=True)

    print("=" * 60, flush=True)
    print("ALL 17 VERIFICATION TESTS PASSED PERFECTLY!", flush=True)
    print("=" * 60, flush=True)

if __name__ == "__main__":
    test_full_system()
