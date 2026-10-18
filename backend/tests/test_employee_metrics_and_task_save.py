import pytest
from fastapi.testclient import TestClient
from app.main import app, create_token, SessionLocal, User, Task

client = TestClient(app)

@pytest.fixture
def test_context():
    db = SessionLocal()
    try:
        hr = db.query(User).filter(User.role == "hr").first()
        mgr = db.query(User).filter(User.role == "manager").first()
        emp_team = (
            db.query(User)
            .filter(User.role == "employee", User.department == mgr.department)
            .first()
        )
        emp_other = (
            db.query(User)
            .filter(
                User.role == "employee",
                User.department != mgr.department,
                User.manager_id != mgr.id,
                User.manager_name != mgr.name,
            )
            .first()
        )
        return {
            "hr": hr,
            "mgr": mgr,
            "emp_team": emp_team,
            "emp_other": emp_other,
        }
    finally:
        db.close()


def test_hr_employee_details_returns_all_seven_metrics(test_context):
    """TASK 1: Verify HR receives all 7 required metrics for an employee."""
    hr = test_context["hr"]
    emp = test_context["emp_team"]
    token = create_token(hr)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/users/{emp.id}/details", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert "profile" in data
    assert data["profile"]["id"] == emp.id
    assert "workload" in data
    assert "wellbeing" in data

    wl = data["workload"]
    wb = data["wellbeing"]

    # 1. Burnout Risk
    assert "burnout_score" in wb
    # 2. Active Tasks
    assert "active_tasks" in wl
    assert isinstance(wl["active_tasks"], int)
    # 3. Completion Rate
    assert "completion_rate" in wl
    assert isinstance(wl["completion_rate"], (int, float))
    # 4. Blocked Tasks
    assert "blocked_tasks" in wl
    assert isinstance(wl["blocked_tasks"], int)
    # 5. Workload Score
    assert "workload_score" in wl
    # 6. Work-Life Balance Score
    assert "work_life_balance_score" in wl
    # 7. Working Hours
    assert "working_hours" in wl
    assert wl["working_hours"] is None or isinstance(wl["working_hours"], str)


def test_manager_team_member_details_returns_all_seven_metrics(test_context):
    """TASK 2: Verify Manager receives all 7 metrics for their authorized team member."""
    mgr = test_context["mgr"]
    emp = test_context["emp_team"]
    token = create_token(mgr)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/users/{emp.id}/details", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    wl = data["workload"]
    wb = data["wellbeing"]

    assert "burnout_score" in wb
    assert "active_tasks" in wl
    assert "completion_rate" in wl
    assert "blocked_tasks" in wl
    assert "workload_score" in wl
    assert "work_life_balance_score" in wl
    assert "working_hours" in wl


def test_manager_blocked_from_unauthorized_employee(test_context):
    """TASK 2: Verify Manager cannot access unauthorized cross-department employee."""
    mgr = test_context["mgr"]
    emp_other = test_context["emp_other"]
    token = create_token(mgr)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/users/{emp_other.id}/details", headers=headers)
    assert res.status_code == 403
    assert "Access forbidden" in res.json().get("detail", "")


def test_task_update_save_and_persistence(test_context):
    """TASK 3: Verify task update saves successfully and persists in database."""
    emp = test_context["emp_team"]
    token = create_token(emp)
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    task = None
    try:
        # Find or create an open task for this employee
        task = db.query(Task).filter(Task.employee_id == emp.id, Task.status != "Completed", Task.status != "Blocked").first()
        if not task:
            task = Task(
                name="Test Save Task",
                employee_id=emp.id,
                status="In Progress",
                priority="Medium",
                completion_percentage=30,
            )
            db.add(task)
            db.commit()
            db.refresh(task)

        task_id = task.id
    finally:
        db.close()

    # Test updating task using string ID with 'T-' prefix
    payload = {
        "progress": 65,
        "work_update": "Automated test progress update verification",
    }
    res = client.put(f"/api/tasks/T-{task_id}", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    res_data = res.json()
    assert res_data["ok"] is True
    assert res_data["progress"] == 65
    assert res_data["work_update"] == "Automated test progress update verification"

    # Verify persisted in database
    db = SessionLocal()
    try:
        updated = db.query(Task).filter(Task.id == task_id).first()
        assert updated is not None
        assert updated.completion_percentage == 65
        assert updated.work_update == "Automated test progress update verification"
    finally:
        db.close()


def test_task_update_validation_errors(test_context):
    """TASK 3: Verify invalid payloads return clear 400 validation errors."""
    emp = test_context["emp_team"]
    token = create_token(emp)
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    task = db.query(Task).filter(
        Task.employee_id == emp.id,
        Task.status.notin_(["Completed", "Blocked"]),
        (Task.completion_percentage < 100) | (Task.completion_percentage == None)
    ).first()
    db.close()

    if task:
        # Invalid progress > 100 on existing active task
        res = client.put(f"/api/tasks/{task.id}", json={"progress": 150}, headers=headers)
        assert res.status_code == 400
        assert "between 0 and 100" in res.json().get("detail", "")
    else:
        # If no active unblocked tasks, verify invalid task still returns 400
        res = client.put("/api/tasks/999999", json={"progress": 150}, headers=headers)
        assert res.status_code in (400, 404)

    # Invalid non-integer task id
    res2 = client.put("/api/tasks/T-INVALID", json={"progress": 50}, headers=headers)
    assert res2.status_code == 400
    assert "Invalid task id" in res2.json().get("detail", "")

