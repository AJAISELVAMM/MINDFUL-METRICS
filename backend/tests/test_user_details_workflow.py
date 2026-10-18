import pytest
from fastapi.testclient import TestClient
from app.main import app, create_token, SessionLocal, User

client = TestClient(app)

@pytest.fixture
def db_users():
    db = SessionLocal()
    try:
        hr = db.query(User).filter(User.role == "hr").first()
        mgr = db.query(User).filter(User.role == "manager").first()
        # Find employee in manager's team
        emp_team = (
            db.query(User)
            .filter(User.role == "employee", User.department == mgr.department)
            .first()
        )
        # Find employee truly outside manager's team
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

def test_hr_can_access_any_employee_details(db_users):
    hr = db_users["hr"]
    emp = db_users["emp_team"]
    token = create_token(hr)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/users/{emp.id}/details", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "profile" in data
    assert data["profile"]["name"] == emp.name
    assert "attendance" in data
    assert "tasks" in data
    assert "leaves" in data
    assert "permissions" in data
    assert "workload" in data
    assert "wellbeing" in data
    assert "total_tasks" in data["workload"]

def test_manager_can_access_team_member_details(db_users):
    mgr = db_users["mgr"]
    emp_team = db_users["emp_team"]
    token = create_token(mgr)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/users/{emp_team.id}/details", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["profile"]["name"] == emp_team.name

def test_manager_blocked_from_cross_department_employee(db_users):
    mgr = db_users["mgr"]
    emp_other = db_users["emp_other"]
    token = create_token(mgr)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/users/{emp_other.id}/details", headers=headers)
    assert res.status_code == 403
    assert "Access forbidden" in res.json().get("detail", "")

def test_employee_can_access_own_details(db_users):
    emp = db_users["emp_team"]
    token = create_token(emp)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/users/{emp.id}/details", headers=headers)
    assert res.status_code == 200
    assert res.json()["profile"]["name"] == emp.name

def test_employee_blocked_from_other_employee_details(db_users):
    emp = db_users["emp_team"]
    emp_other = db_users["emp_other"]
    token = create_token(emp)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/users/{emp_other.id}/details", headers=headers)
    assert res.status_code == 403
    assert "Access forbidden" in res.json().get("detail", "")

def test_user_not_found(db_users):
    hr = db_users["hr"]
    token = create_token(hr)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/users/999999/details", headers=headers)
    assert res.status_code == 404
