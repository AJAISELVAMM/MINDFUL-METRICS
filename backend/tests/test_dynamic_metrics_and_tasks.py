from __future__ import annotations
import pytest
from datetime import date, datetime
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, Task, Survey, Prediction, BurnoutFeatures, Attendance
from app.security import create_token

client = TestClient(app)


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def test_employee(db):
    user = db.query(User).filter(User.email == "test_emp_metrics@mindful.com").first()
    if not user:
        user = User(
            email="test_emp_metrics@mindful.com",
            name="Test Employee Metrics",
            role="employee",
            department="Engineering",
            employee_code="EMP-TEST-99",
            manager_name="Test Manager",
            password_hash="mockhash",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    yield user
    # Teardown
    from app.models import AuditLog
    db.query(AuditLog).filter(AuditLog.actor_id == user.id).delete(synchronize_session=False)
    db.query(Task).filter(Task.employee_id == user.id).delete(synchronize_session=False)
    db.query(Survey).filter(Survey.employee_id == user.id).delete(synchronize_session=False)
    db.query(Prediction).filter(Prediction.employee_id == user.id).delete(synchronize_session=False)
    db.query(BurnoutFeatures).filter(BurnoutFeatures.employee_id == user.id).delete(synchronize_session=False)
    db.query(User).filter(User.id == user.id).delete(synchronize_session=False)
    db.commit()


@pytest.fixture(scope="module")
def other_employee(db):
    user = db.query(User).filter(User.email == "other_emp_metrics@mindful.com").first()
    if not user:
        user = User(
            email="other_emp_metrics@mindful.com",
            name="Other Employee Metrics",
            role="employee",
            department="Engineering",
            employee_code="EMP-OTHER-99",
            manager_name="Test Manager",
            password_hash="mockhash",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    yield user
    # Teardown
    from app.models import AuditLog
    db.query(AuditLog).filter(AuditLog.actor_id == user.id).delete(synchronize_session=False)
    db.query(Task).filter(Task.employee_id == user.id).delete(synchronize_session=False)
    db.query(Survey).filter(Survey.employee_id == user.id).delete(synchronize_session=False)
    db.query(Prediction).filter(Prediction.employee_id == user.id).delete(synchronize_session=False)
    db.query(BurnoutFeatures).filter(BurnoutFeatures.employee_id == user.id).delete(synchronize_session=False)
    db.query(User).filter(User.id == user.id).delete(synchronize_session=False)
    db.commit()


@pytest.fixture(scope="module")
def emp_headers(test_employee):
    token = create_token(test_employee)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def other_headers(other_employee):
    token = create_token(other_employee)
    return {"Authorization": f"Bearer {token}"}


def setup_8_tasks_scenario(db, user):
    """
    Initial state required by Section 3 and Section 12:
    - Total tasks: 8
    - Blocked: 2
    - In Progress: 4
    - Completed: 2
    """
    # Clean old tasks for this user
    db.query(Task).filter(Task.employee_id == user.id).delete()
    db.commit()

    tasks_to_create = [
        {"name": "Blocked Task 1", "status": "Blocked", "progress": 25, "blocked_reason": "Waiting on external API"},
        {"name": "Blocked Task 2", "status": "Blocked", "progress": 30, "blocked_reason": "Waiting for credentials"},
        {"name": "In Progress Task 1", "status": "In Progress", "progress": 40},
        {"name": "In Progress Task 2", "status": "In Progress", "progress": 50},
        {"name": "In Progress Task 3", "status": "In Progress", "progress": 60},
        {"name": "In Progress Task 4", "status": "In Progress", "progress": 70},
        {"name": "Completed Task 1", "status": "Completed", "progress": 100},
        {"name": "Completed Task 2", "status": "Completed", "progress": 100},
    ]

    created = []
    for t_spec in tasks_to_create:
        t = Task(
            employee_id=user.id,
            name=t_spec["name"],
            status=t_spec["status"],
            completion_percentage=t_spec["progress"],
            blocked_reason=t_spec.get("blocked_reason"),
            completed_at=datetime.utcnow() if t_spec["status"] == "Completed" else None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(t)
        created.append(t)
    db.commit()
    for t in created:
        db.refresh(t)
    return created


def test_scenario_a_and_e_task_completion_and_persistence(db, test_employee, emp_headers):
    """
    Test A & E:
    Initial state: 8 total tasks (2 Blocked, 4 In Progress, 2 Completed).
    Complete 1 In Progress task.
    Verify: 8 Total, 2 Blocked, 3 In Progress, 3 Completed.
    Verify status remains Completed in PostgreSQL in a fresh session.
    """
    tasks = setup_8_tasks_scenario(db, test_employee)
    in_progress_tasks = [t for t in tasks if t.status == "In Progress"]
    assert len(in_progress_tasks) == 4
    target_task = in_progress_tasks[0]

    # Pre-check initial summary
    res_before = client.get("/api/tasks/my", headers=emp_headers)
    assert res_before.status_code == 200
    summary_before = res_before.json()["summary"]
    assert summary_before["assigned"] == 8
    assert summary_before["blocked"] == 2
    assert summary_before["in_progress"] == 4
    assert summary_before["completed"] == 2

    # Complete 1 task from In Progress
    res_update = client.patch(
        f"/api/tasks/T-{target_task.id}",
        json={"status": "Completed", "progress": 100},
        headers=emp_headers,
    )
    assert res_update.status_code == 200
    body = res_update.json()
    assert body["status"] == "Completed"
    assert body["progress"] == 100

    # Fetch updated tasks summary via API
    res_after = client.get("/api/tasks/my", headers=emp_headers)
    assert res_after.status_code == 200
    summary_after = res_after.json()["summary"]
    assert summary_after["assigned"] == 8
    assert summary_after["blocked"] == 2
    assert summary_after["in_progress"] == 3
    assert summary_after["completed"] == 3

    # Test E: Verify PostgreSQL persistence in a fresh session
    fresh_session = SessionLocal()
    try:
        persisted = fresh_session.query(Task).filter(Task.id == target_task.id).first()
        assert persisted is not None
        assert persisted.status == "Completed"
        assert persisted.completion_percentage == 100
        assert persisted.completed_at is not None
    finally:
        fresh_session.close()


def test_scenario_b_workload_recomputation(db, test_employee, emp_headers):
    """
    Test B:
    Verify that completing a task dynamically updates the workload calculation:
    Pending tasks drops from 6 to 5.
    workload_deviation drops by 6.0 points ((5-3)*6 vs (6-3)*6).
    The dashboard KPI returns the updated workload value.
    """
    tasks = setup_8_tasks_scenario(db, test_employee)
    in_progress = [t for t in tasks if t.status == "In Progress"]

    # 1. Check dashboard before task completion
    dash_before = client.get("/api/employee/dashboard", headers=emp_headers)
    assert dash_before.status_code == 200
    wl_before = dash_before.json()["kpis"]["workloadScore"]

    # 2. Complete 1 In Progress task
    target_task = in_progress[0]
    res_update = client.patch(
        f"/api/tasks/T-{target_task.id}",
        json={"status": "Completed", "progress": 100},
        headers=emp_headers,
    )
    assert res_update.status_code == 200

    # 3. Check dashboard after task completion
    dash_after = client.get("/api/employee/dashboard", headers=emp_headers)
    assert dash_after.status_code == 200
    wl_after = dash_after.json()["kpis"]["workloadScore"]

    # Workload score must have decreased by exactly 6 points (or reflect the lower pending workload)
    assert wl_after < wl_before
    assert wl_before - wl_after == 6


def test_scenario_c_work_life_balance_independence_and_survey_update(db, test_employee, emp_headers):
    """
    Test C:
    Verify that task completion alone does not artificially alter Work-Life Balance.
    Then verify that when a new wellbeing survey is submitted, WLB reflects it accurately.
    """
    tasks = setup_8_tasks_scenario(db, test_employee)
    in_progress = [t for t in tasks if t.status == "In Progress"]

    # Add survey with WLB = 4 (which is 80)
    survey = Survey(
        employee_id=test_employee.id,
        survey_type="daily",
        date=date.today(),
        answers={"wlb": 4, "stress": 2, "workload": 3},
    )
    db.add(survey)
    db.commit()

    dash_1 = client.get("/api/employee/dashboard", headers=emp_headers).json()
    wlb_1 = dash_1["kpis"]["wlbScore"]
    assert wlb_1 == 80  # 4 * 20 = 80

    # Complete a task
    target = in_progress[0]
    client.patch(f"/api/tasks/T-{target.id}", json={"status": "Completed", "progress": 100}, headers=emp_headers)

    # WLB must NOT change simply because a task was completed
    dash_2 = client.get("/api/employee/dashboard", headers=emp_headers).json()
    wlb_2 = dash_2["kpis"]["wlbScore"]
    assert wlb_2 == 80, "Task completion must not artificially alter WLB"

    # Submit a new survey with WLB = 1 (20)
    survey_new = Survey(
        employee_id=test_employee.id,
        survey_type="daily",
        date=date.today(),
        answers={"wlb": 1, "stress": 4, "workload": 4},
    )
    db.add(survey_new)
    db.commit()

    # WLB must now reflect the new survey: 1 * 20 = 20
    dash_3 = client.get("/api/employee/dashboard", headers=emp_headers).json()
    wlb_3 = dash_3["kpis"]["wlbScore"]
    assert wlb_3 == 20


def test_scenario_f_employee_isolation(db, test_employee, other_employee, emp_headers, other_headers):
    """
    Test F:
    Updating one employee's task must not modify another employee's tasks or metrics.
    """
    setup_8_tasks_scenario(db, test_employee)
    setup_8_tasks_scenario(db, other_employee)

    # Initial dashboard for other employee
    other_before = client.get("/api/employee/dashboard", headers=other_headers).json()
    other_tasks_before = client.get("/api/tasks/my", headers=other_headers).json()

    # Complete a task for test_employee
    emp_tasks = client.get("/api/tasks/my", headers=emp_headers).json()["tasks"]
    emp_in_progress = next(t for t in emp_tasks if t["status"] == "In Progress")
    client.patch(f"/api/tasks/{emp_in_progress['id']}", json={"status": "Completed", "progress": 100}, headers=emp_headers)

    # Check other employee's dashboard and task summary
    other_after = client.get("/api/employee/dashboard", headers=other_headers).json()
    other_tasks_after = client.get("/api/tasks/my", headers=other_headers).json()

    assert other_tasks_before["summary"]["completed"] == other_tasks_after["summary"]["completed"]
    assert other_tasks_before["summary"]["in_progress"] == other_tasks_after["summary"]["in_progress"]
    assert other_before["kpis"]["workloadScore"] == other_after["kpis"]["workloadScore"]


def test_scenario_g_error_handling(db, test_employee, other_employee, emp_headers):
    """
    Test G:
    Test unauthorized updates (employee modifying another employee's task),
    non-existent tasks, and invalid progress values.
    """
    other_task = Task(
        employee_id=other_employee.id,
        name="Private Other Task",
        status="In Progress",
        completion_percentage=50,
        created_at=datetime.utcnow(),
    )
    db.add(other_task)
    db.commit()
    db.refresh(other_task)

    # 1. Unauthorized task update (employee A trying to update employee B's task)
    res_unauth = client.patch(
        f"/api/tasks/T-{other_task.id}",
        json={"status": "Completed", "progress": 100},
        headers=emp_headers,
    )
    assert res_unauth.status_code == 403

    # 2. Non-existent task update
    res_not_found = client.patch(
        "/api/tasks/T-99999999",
        json={"status": "Completed"},
        headers=emp_headers,
    )
    assert res_not_found.status_code == 404

    # 3. Invalid completion progress (<100 for Completed status)
    emp_task = db.query(Task).filter(Task.employee_id == test_employee.id).first()
    res_invalid = client.patch(
        f"/api/tasks/T-{emp_task.id}",
        json={"status": "Completed", "progress": 50},
        headers=emp_headers,
    )
    assert res_invalid.status_code == 400
