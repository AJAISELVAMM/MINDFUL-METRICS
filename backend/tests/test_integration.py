from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


ROLE_MAP = {
    "employee@mindfulmetrics.com": ("vignesh@gmail.com", "Vignesh@123"),
    "manager@mindfulmetrics.com": ("aakas@gmail.com", "Aakas@123"),
    "hr@mindfulmetrics.com": ("ajai@gmail.com", "Ajai@123"),
}


def get_token(email: str, password: str = "demo123") -> str:
    target_email, target_pw = ROLE_MAP.get(email, (email, password))
    res = client.post("/api/auth/login", json={"email": target_email, "password": target_pw})
    if res.status_code != 200:
        res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["token"]


def test_auth_and_roles():
    emp_tok = get_token("employee@mindfulmetrics.com")
    mgr_tok = get_token("manager@mindfulmetrics.com")
    hr_tok = get_token("hr@mindfulmetrics.com")

    # Employee cannot access HR dashboard
    res_forbidden = client.get("/api/hr/dashboard", headers={"Authorization": f"Bearer {emp_tok}"})
    assert res_forbidden.status_code == 403

    # Manager cannot access HR dashboard
    res_mgr_forbidden = client.get("/api/hr/dashboard", headers={"Authorization": f"Bearer {mgr_tok}"})
    assert res_mgr_forbidden.status_code == 403

    # HR can access HR dashboard
    res_hr = client.get("/api/hr/dashboard", headers={"Authorization": f"Bearer {hr_tok}"})
    assert res_hr.status_code == 200
    assert "totalEmployees" in res_hr.json()


def test_manager_is_also_employee():
    mgr_tok = get_token("manager@mindfulmetrics.com")
    headers = {"Authorization": f"Bearer {mgr_tok}"}

    # Manager can get their own attendance
    res_att = client.get("/api/attendance/weekly", headers=headers)
    assert res_att.status_code == 200
    assert "weekly" in res_att.json()

    # Manager can get their own leave
    res_leave = client.get("/api/leave/my", headers=headers)
    assert res_leave.status_code == 200
    assert "balance" in res_leave.json()

    # Manager can get team leave requests
    res_team_leave = client.get("/api/leave/team", headers=headers)
    assert res_team_leave.status_code == 200

    # Manager can get manager survey questions
    res_survey = client.get("/api/survey/questions", headers=headers)
    assert res_survey.status_code == 200
    assert "management" in res_survey.json()


def test_hr_leave_management():
    hr_tok = get_token("hr@mindfulmetrics.com")
    headers = {"Authorization": f"Bearer {hr_tok}"}

    res = client.get("/api/leave/all", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    if data:
        first = data[0]
        assert "employee" in first
        assert "employee_id" in first
        assert "department" in first
        assert "role" in first
        assert "leave_type" in first


def test_hr_model_performance():
    hr_tok = get_token("hr@mindfulmetrics.com")
    headers = {"Authorization": f"Bearer {hr_tok}"}

    res = client.get("/api/hr/model-performance", headers=headers)
    assert res.status_code == 200
    perf = res.json()
    assert "models" in perf
    assert len(perf["models"]) >= 1
    assert "features" in perf
    assert "confusion" in perf


def test_pulse_survey():
    emp_tok = get_token("employee@mindfulmetrics.com")
    headers = {"Authorization": f"Bearer {emp_tok}"}

    res = client.post("/api/survey/pulse", json={"workload": "Moderate"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_task_update_and_blocker_workflow():
    emp_tok = get_token("employee@mindfulmetrics.com")
    headers = {"Authorization": f"Bearer {emp_tok}"}

    # Fetch tasks
    my_tasks = client.get("/api/tasks/my", headers=headers).json()
    assert len(my_tasks["tasks"]) > 0
    first_task = next((t for t in my_tasks["tasks"] if t.get("status") not in ("Completed", "Blocked")), None)
    created_temp = False
    if not first_task:
        mgr_tok = get_token("manager@mindfulmetrics.com")
        c_res = client.post(
            "/api/tasks",
            json={"name": "Temporary Feature Task", "assigned_to": "E201", "priority": "Medium", "deadline": "Tomorrow"},
            headers={"Authorization": f"Bearer {mgr_tok}"},
        )
        assert c_res.status_code == 200
        first_task = {"id": c_res.json()["id"]}
        created_temp = True

    try:
        # Update task details with progress, work update, and blocker
        update_payload = {
            "status": "Blocked",
            "progress": 75,
            "work_update": "Implemented database schema, waiting on API credentials.",
            "blocked_reason": "Waiting for backend team credentials.",
        }
        res = client.put(f"/api/tasks/{first_task['id']}", json=update_payload, headers=headers)
        assert res.status_code == 200
        updated = res.json()["task"]
        assert updated["status"] == "Blocked"
        assert updated["progress"] == 75
        assert updated["blocked_reason"] == "Waiting for backend team credentials."
    finally:
        if created_temp:
            from app.database import SessionLocal
            from app.models import Task
            db = SessionLocal()
            try:
                raw_id = int(str(first_task["id"]).replace("T-", ""))
                db.query(Task).filter(Task.id == raw_id).delete()
                db.commit()
            finally:
                db.close()


def test_leave_and_permission_cancellation():
    emp_tok = get_token("employee@mindfulmetrics.com")
    headers = {"Authorization": f"Bearer {emp_tok}"}

    # Apply leave
    leave_res = client.post(
        "/api/leave",
        json={"type": "Casual Leave", "start": "2026-11-01", "end": "2026-11-01", "reason": "Personal work"},
        headers=headers,
    )
    assert leave_res.status_code == 200
    leave_id = leave_res.json()["item"]["id"]

    # Cancel leave
    cancel_res = client.delete(f"/api/leave/{leave_id}", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["ok"] is True

    # Apply permission
    perm_res = client.post(
        "/api/permission",
        json={"date": "2026-11-02", "requested_checkout_time": "04:30 PM", "reason": "Doctor appointment"},
        headers=headers,
    )
    assert perm_res.status_code == 200
    perm_id = perm_res.json()["item"]["id"]

    # Cancel permission
    cancel_p_res = client.delete(f"/api/permission/{perm_id}", headers=headers)
    assert cancel_p_res.status_code == 200
    assert cancel_p_res.json()["ok"] is True


def test_manager_and_hr_trends():
    mgr_tok = get_token("manager@mindfulmetrics.com")
    mgr_headers = {"Authorization": f"Bearer {mgr_tok}"}
    m_trends = client.get("/api/manager/trends", headers=mgr_headers)
    assert m_trends.status_code == 200
    assert "burnout_trend" in m_trends.json()

    hr_tok = get_token("hr@mindfulmetrics.com")
    hr_headers = {"Authorization": f"Bearer {hr_tok}"}
    hr_trends = client.get("/api/hr/trends", headers=hr_headers)
    assert hr_trends.status_code == 200
    assert "trends" in hr_trends.json()


def test_ai_chat_rbac_privacy():
    emp_tok = get_token("employee@mindfulmetrics.com")
    emp_headers = {"Authorization": f"Bearer {emp_tok}"}

    # Employee asking about peer's risk score should be blocked by privacy check
    res = client.post("/api/ai/chat", json={"text": "What is Arjun or Rahul's burnout risk score?", "role": "Employee"}, headers=emp_headers)
    assert res.status_code == 200
    reply = res.json()["reply"]
    assert "confidential" in reply.lower() or "privacy" in reply.lower()

    # Employee asking about own work progress
    res_own = client.post("/api/ai/chat", json={"text": "How are my tasks doing this week?", "role": "Employee"}, headers=emp_headers)
    assert res_own.status_code == 200
    assert len(res_own.json()["reply"]) > 10


def test_short_session_attendance_exception():
    from datetime import date, time, datetime
    from app.services.attendance_service import calculate_attendance_rule
    from app.models import CompanySettings

    settings = CompanySettings(
        work_start_time="09:00",
        checkin_grace_time="09:30",
        afternoon_start_time="13:00",
        early_checkout_threshold="17:00",
        work_end_time="17:30",
        timezone="Asia/Kolkata",
    )
    d = date(2026, 10, 6)
    cin = datetime.combine(d, time(12, 18))
    cout = datetime.combine(d, time(12, 19))
    # 12:18 PM to 12:19 PM (1 minute work session)
    rule = calculate_attendance_rule(
        settings,
        cin,
        cout,
    )
    assert rule["final_status"] == "ATTENDANCE_EXCEPTION"
    assert rule["exception_code"] == "SHORT_SESSION_EXCEPTION"


def test_dynamic_hr_interventions():
    hr_tok = get_token("hr@mindfulmetrics.com")
    emp_tok = get_token("employee@mindfulmetrics.com")
    hr_headers = {"Authorization": f"Bearer {hr_tok}"}
    emp_headers = {"Authorization": f"Bearer {emp_tok}"}

    # Employee cannot access HR interventions
    emp_res = client.get("/api/hr/interventions", headers=emp_headers)
    assert emp_res.status_code == 403

    # HR gets candidates
    cand_res = client.get("/api/hr/interventions/candidates", headers=hr_headers)
    assert cand_res.status_code == 200
    assert isinstance(cand_res.json(), list)

    int_id = None
    try:
        # HR creates intervention for employee (E201)
        create_payload = {
            "employee_id": "E201",
            "risk_level": "High",
            "trigger_reason": "Consistent overtime and high burnout score",
            "intervention_type": "Workload Review",
            "recommendation": "Redistribute sprint tasks and hold 1-on-1 check-in",
            "status": "OPEN",
            "follow_up_date": "2026-10-25",
            "notes": "Initial case opened after analytics alert.",
        }
        create_res = client.post("/api/hr/interventions", json=create_payload, headers=hr_headers)
        assert create_res.status_code == 200
        created = create_res.json()
        assert created["ok"] is True
        int_id = created["id"]
        assert int_id.startswith("INT-")
        assert created["status"] == "OPEN"
        assert created["risk_level"] == "High"

        # HR lists interventions and finds the newly created one
        list_res = client.get("/api/hr/interventions", headers=hr_headers)
        assert list_res.status_code == 200
        items = list_res.json()
        assert any(i["id"] == int_id for i in items)

        # HR updates status to IN_PROGRESS
        patch_res = client.patch(
            f"/api/hr/interventions/{int_id}",
            json={"status": "IN_PROGRESS", "notes": "Meeting held with manager Aakas; task redistribution started."},
            headers=hr_headers,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "IN_PROGRESS"

        # HR marks intervention RESOLVED with resolution note
        resolve_res = client.patch(
            f"/api/hr/interventions/{int_id}",
            json={"status": "RESOLVED", "resolution": "Weekly hours normalized to 40; risk reduced to healthy levels."},
            headers=hr_headers,
        )
        assert resolve_res.status_code == 200
        assert resolve_res.json()["status"] == "RESOLVED"
        assert "Weekly hours normalized" in resolve_res.json()["resolution"]
    finally:
        if int_id:
            from app.database import SessionLocal
            from app.models import Intervention
            db = SessionLocal()
            try:
                num_id = int(str(int_id).replace("INT-", ""))
                db.query(Intervention).filter(Intervention.id == num_id).delete()
                db.commit()
            finally:
                db.close()


def test_hr_to_manager_task_assignment_workflow():
    hr_tok = get_token("hr@mindfulmetrics.com")
    mgr_tok = get_token("manager@mindfulmetrics.com")
    emp_tok = get_token("employee@mindfulmetrics.com")

    hr_headers = {"Authorization": f"Bearer {hr_tok}"}
    mgr_headers = {"Authorization": f"Bearer {mgr_tok}"}
    emp_headers = {"Authorization": f"Bearer {emp_tok}"}

    task_id = None
    try:
        # 1. HR creates an organizational task assigned to Manager (Aakas, M101)
        create_task_res = client.post(
            "/api/tasks",
            json={
                "name": "Q3 Engineering Workload Assessment",
                "description": "Assess team sprint workload distribution and balance hours.",
                "priority": "High",
                "deadline": "25 Oct",
                "assigned_to": "M101",
            },
            headers=hr_headers,
        )
        assert create_task_res.status_code == 200
        task_data = create_task_res.json()
        assert task_data["ok"] is True
        task_id = task_data["id"]

        # 2. Manager logs in, fetches their own assigned tasks (/api/tasks/my)
        mgr_tasks_res = client.get("/api/tasks/my", headers=mgr_headers)
        assert mgr_tasks_res.status_code == 200
        my_tasks = mgr_tasks_res.json()["tasks"]
        matching = [t for t in my_tasks if t["id"] == task_id or t.get("raw_id") == int(task_id.replace("T-", ""))]
        assert len(matching) > 0, "Manager should see the task assigned by HR"

        # 3. Manager updates task progress to 50%
        update_res = client.put(
            f"/api/tasks/{task_id}",
            json={"status": "In Progress", "progress": 50, "work_update": "Audit completed for 4 developers."},
            headers=mgr_headers,
        )
        assert update_res.status_code == 200
        assert update_res.json()["progress"] == 50

        # 4. HR views all tasks (/api/tasks/all) and sees updated progress
        all_tasks_res = client.get("/api/tasks/all", headers=hr_headers)
        assert all_tasks_res.status_code == 200
        hr_all_tasks = all_tasks_res.json()["tasks"]
        hr_matching = [t for t in hr_all_tasks if t["id"] == task_id or t.get("raw_id") == int(task_id.replace("T-", ""))]
        assert len(hr_matching) > 0
        assert hr_matching[0]["progress"] == 50
        assert hr_matching[0]["work_update"] == "Audit completed for 4 developers."

        # 5. Task validation: Blocked status requires blocker_reason
        invalid_blocked_res = client.put(
            f"/api/tasks/{task_id}",
            json={"status": "Blocked", "blocked_reason": ""},
            headers=mgr_headers,
        )
        assert invalid_blocked_res.status_code in (400, 404), "Should reject Blocked status without blocker reason"

        # 6. Task validation: Completed status sets/requires 100%
        invalid_completed_res = client.put(
            f"/api/tasks/{task_id}",
            json={"status": "Completed", "progress": 45},
            headers=mgr_headers,
        )
        assert invalid_completed_res.status_code in (400, 404), "Should reject Completed status with 45% progress"

        # 7. Valid completion sets 100%
        valid_completed_res = client.put(
            f"/api/tasks/{task_id}",
            json={"status": "Completed", "progress": 100},
            headers=mgr_headers,
        )
        assert valid_completed_res.status_code == 200
        assert valid_completed_res.json()["progress"] == 100
        assert valid_completed_res.json()["status"] == "Completed"

        # 8. RBAC: Employee cannot assign task to another user
        emp_assign_res = client.post(
            "/api/tasks",
            json={"name": "Unauthorized Task", "assigned_to": "M101"},
            headers=emp_headers,
        )
        assert emp_assign_res.status_code in (400, 403, 500)
    finally:
        if task_id:
            from app.database import SessionLocal
            from app.models import Task
            db = SessionLocal()
            try:
                raw_id = int(str(task_id).replace("T-", ""))
                db.query(Task).filter(Task.id == raw_id).delete()
                db.commit()
            finally:
                db.close()


def test_scenario_1_employee_complete_flow():
    # 1. Employee login
    emp_tok = get_token("employee@mindfulmetrics.com")
    headers = {"Authorization": f"Bearer {emp_tok}"}

    # 2. Check in (or verify today's checkin status)
    checkin_res = client.post("/api/attendance/check-in", headers=headers)
    assert checkin_res.status_code in (200, 400)  # 200 or 400 if already checked in

    # 3. Submit morning wellbeing
    survey_res = client.post(
        "/api/survey/daily?survey_type=morning",
        json={"answers": {"stress": 3, "energy": 4, "manageable": 3, "satisfied": 4, "wlb": 4}},
        headers=headers,
    )
    assert survey_res.status_code == 200

    # 4. View tasks
    tasks_res = client.get("/api/tasks/my", headers=headers)
    assert tasks_res.status_code == 200
    tasks = tasks_res.json()["tasks"]
    assert len(tasks) > 0
    editable_task = next((t for t in tasks if t.get("status") not in ("Completed", "Blocked")), None)
    created_task_id = None
    if not editable_task:
        mgr_tok = get_token("manager@mindfulmetrics.com")
        c_res = client.post(
            "/api/tasks",
            json={"name": "Core Dev Sprint Task", "assigned_to": "E201", "priority": "High", "deadline": "Tomorrow"},
            headers={"Authorization": f"Bearer {mgr_tok}"},
        )
        assert c_res.status_code == 200
        t_id = c_res.json()["id"]
        created_task_id = t_id
    else:
        t_id = editable_task["id"]

    try:
        # 5. Update progress & submit work update text
        work_update_res = client.put(
            f"/api/tasks/{t_id}",
            json={
                "status": "In Progress",
                "progress": 65,
                "work_update": "Completed unit tests and refactored core database handlers successfully.",
            },
            headers=headers,
        )
        assert work_update_res.status_code == 200
        assert work_update_res.json()["progress"] == 65

        # 6. Burnout model recalculates via /api/ai/predict-burnout or /api/employee/burnout
        pred_res = client.post("/api/ai/predict-burnout", headers=headers)
        assert pred_res.status_code == 200
        pred = pred_res.json()
        assert "burnout_score" in pred
        assert "risk_level" in pred
        assert "recommendations" in pred
        assert isinstance(pred["recommendations"], list)

        # 7. Employee sees updated insight on dashboard
        dash_res = client.get("/api/employee/dashboard", headers=headers)
        assert dash_res.status_code == 200
        dash = dash_res.json()
        assert "kpis" in dash
        assert "burnoutRisk" in dash["kpis"]
    finally:
        if created_task_id:
            from app.database import SessionLocal
            from app.models import Task
            db = SessionLocal()
            try:
                raw_id = int(str(created_task_id).replace("T-", ""))
                db.query(Task).filter(Task.id == raw_id).delete()
                db.commit()
            finally:
                db.close()


def test_scenario_2_manager_complete_flow():
    # 1. Manager login
    mgr_tok = get_token("manager@mindfulmetrics.com")
    emp_tok = get_token("employee@mindfulmetrics.com")
    mgr_headers = {"Authorization": f"Bearer {mgr_tok}"}
    emp_headers = {"Authorization": f"Bearer {emp_tok}"}

    # 2. Manager check in
    mgr_cin = client.post("/api/attendance/check-in", headers=mgr_headers)
    assert mgr_cin.status_code in (200, 400)

    # 3. Manager views team
    team_res = client.get("/api/manager/team", headers=mgr_headers)
    assert team_res.status_code == 200
    members = team_res.json()
    assert len(members) > 0

    task_id = None
    try:
        # 4. Manager creates task for employee Vignesh (E201)
        task_res = client.post(
            "/api/tasks",
            json={
                "name": "Implement Secure Session Vault",
                "description": "Build high-security cryptographic session vault for auth tokens.",
                "priority": "High",
                "deadline": "28 Oct",
                "assigned_to": "E201",
            },
            headers=mgr_headers,
        )
        assert task_res.status_code == 200
        task_id = task_res.json()["id"]

        # 5. Employee logs in, sees task, updates to Blocked with blocker reason
        emp_upd_res = client.put(
            f"/api/tasks/{task_id}",
            json={
                "status": "Blocked",
                "progress": 30,
                "blocked_reason": "Missing cloud HSM encryption key from ops team.",
                "work_update": "Core crypto logic drafted; blocked on key access.",
            },
            headers=emp_headers,
        )
        assert emp_upd_res.status_code == 200
        assert emp_upd_res.json()["task"]["status"] == "Blocked"

        # 6. Manager views team workload and sees blocker & progress
        workload_res = client.get("/api/tasks/team", headers=mgr_headers)
        assert workload_res.status_code == 200
        team_tasks = workload_res.json()["tasks"]
        matching = [t for t in team_tasks if t.get("name") == "Implement Secure Session Vault" and "Missing cloud HSM" in (t.get("blocked_reason") or "")]
        assert len(matching) > 0
        assert matching[0]["status"] == "Blocked"
    finally:
        if task_id:
            from app.database import SessionLocal
            from app.models import Task
            db = SessionLocal()
            try:
                raw_id = int(str(task_id).replace("T-", ""))
                db.query(Task).filter(Task.id == raw_id).delete()
                db.commit()
            finally:
                db.close()




