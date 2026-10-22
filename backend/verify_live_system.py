"""
Comprehensive End-to-End Verification Script against Live Running FastAPI Server.
Uses standard library urllib to avoid extra dependencies.
"""
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"

def req(path, method="GET", data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(r) as resp:
        res_body = resp.read().decode("utf-8")
        return resp.status, json.loads(res_body) if res_body else None

def test_live_system():
    print("=" * 60)
    print("MINDFUL METRICS - LIVE RUNNING SYSTEM E2E VERIFICATION")
    print("=" * 60)

    # 1. Health check
    status, body = req("/api/health")
    assert status == 200, f"Health check failed: {status}"
    print("[PASS] 1. Live Backend Health Check OK")

    # 2. HR Login & Verification
    status, hr_data = req("/api/auth/login", method="POST", data={"email": "ajai@gmail.com", "password": "Ajai@123"})
    assert status == 200, f"HR login failed: {hr_data}"
    hr_token = hr_data["token"]
    hr_user = hr_data["user"]
    assert hr_user["role"].lower() == "hr"
    print(f"[PASS] 2. HR Login OK: {hr_user['name']} (role={hr_user['role']})")

    # HR Dashboard
    status, dash_data = req("/api/hr/dashboard", token=hr_token)
    assert status == 200, f"HR dashboard failed"
    assert "kpis" in dash_data
    print(f"       HR Dashboard KPIs: total_employees={dash_data['kpis'].get('total_employees')}, high_risk={dash_data['kpis'].get('high_risk')}")

    # HR Employees
    status, employees = req("/api/hr/employees", token=hr_token)
    assert status == 200
    assert len(employees) > 0
    print(f"[PASS] 3. HR Employees Page API OK: {len(employees)} employees returned")

    # HR Attendance - Verify NO false HOLIDAY
    status, att_data = req("/api/hr/attendance?date=2026-10-22", token=hr_token)
    assert status == 200
    att_records = att_data if isinstance(att_data, list) else att_data.get("attendance", [])
    print(f"[PASS] 4. HR Attendance API OK: {len(att_records)} records for 2026-10-22 (Thursday)")
    
    # Check that employees on 2026-10-22 without check-in are NOT HOLIDAY
    holiday_count = 0
    working_or_absent_count = 0
    for rec in att_records:
        status_text = rec.get("status", "")
        if "holiday" in status_text.lower():
            holiday_count += 1
        else:
            working_or_absent_count += 1
    print(f"       Attendance Status Check on regular weekday: {working_or_absent_count} active/absent/working, {holiday_count} holidays")
    assert holiday_count == 0, f"CRITICAL: Found {holiday_count} false HOLIDAY statuses on working Thursday 2026-10-22!"
    print(f"[PASS] 5. Verified Attendance HOLIDAY Bug Fix: 0 false holidays on working weekday!")

    # HR Leave
    status, leaves = req("/api/hr/leave", token=hr_token)
    assert status == 200
    print(f"[PASS] 6. HR Leave API OK: {len(leaves)} leave requests")

    # HR Tasks
    status, tasks = req("/api/tasks", token=hr_token)
    assert status == 200
    print(f"[PASS] 7. HR Tasks API OK: {len(tasks)} tasks")

    # HR Interventions
    status, interv = req("/api/interventions", token=hr_token)
    assert status == 200
    print(f"[PASS] 8. HR Interventions API OK: {len(interv)} interventions")

    # 3. Employee Login & Verification
    status, emp_data = req("/api/auth/login", method="POST", data={"email": "vignesh@gmail.com", "password": "Vignesh@123"})
    assert status == 200
    emp_token = emp_data["token"]
    emp_user = emp_data["user"]
    assert emp_user["role"].lower() == "employee"
    print(f"[PASS] 9. Employee Login OK: {emp_user['name']} (role={emp_user['role']})")

    # Employee Dashboard
    status, emp_dash_data = req("/api/employee/dashboard", token=emp_token)
    assert status == 200
    assert "kpis" in emp_dash_data
    print(f"[PASS] 10. Employee Dashboard API OK: burnout_score={emp_dash_data['kpis'].get('burnout_score')}")

    # Employee Details Drawer
    status, det_data = req(f"/api/users/{emp_user['id']}/details", token=emp_token)
    assert status == 200
    assert det_data["profile"]["name"] == emp_user["name"]
    print(f"[PASS] 11. Employee Profile Details API OK: Verified authentic user {det_data['profile']['name']}")

    # Employee Tasks
    status, emp_tasks = req("/api/tasks", token=emp_token)
    assert status == 200
    print(f"[PASS] 12. Employee Tasks API OK: {len(emp_tasks)} tasks returned for employee")

    # Employee Trends
    status, emp_trends = req("/api/employee/trends", token=emp_token)
    assert status == 200
    print(f"[PASS] 13. Employee Trends API OK: {len(emp_trends)} trend records")

    # 4. Manager Login & Verification
    status, mgr_data = req("/api/auth/login", method="POST", data={"email": "aakas@gmail.com", "password": "Aakas@123"})
    assert status == 200
    mgr_token = mgr_data["token"]
    status, mgr_dash = req("/api/manager/dashboard", token=mgr_token)
    assert status == 200
    print(f"[PASS] 14. Manager Dashboard API OK")

    print("=" * 60)
    print("ALL 14 E2E SYSTEM TESTS PASSED ON LIVE RUNNING SERVERS!")
    print("=" * 60)

if __name__ == "__main__":
    test_live_system()
