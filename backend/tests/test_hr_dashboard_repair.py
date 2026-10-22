from __future__ import annotations
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User
from app.security import create_token

client = TestClient(app)


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def hr_token(db):
    hr = db.query(User).filter(User.role == "hr").first()
    assert hr is not None, "HR user must exist in the database"
    return create_token(hr)


@pytest.fixture(scope="module")
def emp_token(db):
    emp = db.query(User).filter(User.role == "employee").first()
    assert emp is not None, "Employee user must exist in the database"
    return create_token(emp)


def test_hr_dashboard_loads_real_metrics_and_fast(hr_token):
    t0 = time.time()
    resp = client.get("/api/hr/dashboard", headers={"Authorization": f"Bearer {hr_token}"})
    duration = time.time() - t0

    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"
    data = resp.json()

    # Performance requirement: must complete in under 15 seconds
    assert duration < 15.0, f"Dashboard took too long: {duration:.2f}s"

    # Shape and values requirement
    assert "totalEmployees" in data
    assert data["totalEmployees"] > 0
    assert "highRisk" in data
    assert "modRisk" in data
    assert "lowRisk" in data
    assert data["totalEmployees"] == data["highRisk"] + data["modRisk"] + data["lowRisk"]

    assert "dist" in data
    assert len(data["dist"]) == 3

    assert "departments" in data
    assert len(data["departments"]) > 0
    for dept in data["departments"]:
        assert "name" in dept
        assert "risk" in dept
        assert "workload" in dept

    assert "trend" in data
    assert len(data["trend"]) == 6
    for t in data["trend"]:
        assert "month" in t
        assert "burnout" in t
        assert "workload" in t


def test_hr_employees_loads_all_records_accurately(hr_token, db):
    expected_count = db.query(User).filter(User.role.in_(["employee", "manager"])).count()
    t0 = time.time()
    resp = client.get("/api/hr/employees", headers={"Authorization": f"Bearer {hr_token}"})
    duration = time.time() - t0

    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"
    employees = resp.json()

    assert duration < 15.0, f"Employees took too long: {duration:.2f}s"
    assert len(employees) == expected_count, f"Expected {expected_count} employees, got {len(employees)}"

    # Check variation across employees (burnout/workload scores not identical constants)
    burnout_scores = set(e["burnout"] for e in employees if e.get("burnout") is not None)
    assert len(burnout_scores) > 1, f"Burnout scores must not be identical across all employees: {burnout_scores}"


def test_hr_departments_endpoint_fast_and_accurate(hr_token):
    t0 = time.time()
    resp = client.get("/api/hr/departments", headers={"Authorization": f"Bearer {hr_token}"})
    duration = time.time() - t0

    assert resp.status_code == 200
    depts = resp.json()
    assert duration < 15.0, f"Departments took too long: {duration:.2f}s"
    assert len(depts) > 0
    for d in depts:
        assert "name" in d
        assert "risk" in d
        assert "workload" in d
        assert "stress" in d


def test_hr_trends_endpoint(hr_token):
    t0 = time.time()
    resp = client.get("/api/hr/trends", headers={"Authorization": f"Bearer {hr_token}"})
    duration = time.time() - t0

    assert resp.status_code == 200
    data = resp.json()
    assert duration < 15.0, f"Trends took too long: {duration:.2f}s"
    assert "trend" in data
    assert len(data["trend"]) == 6


def test_user_full_details_isolation_and_correctness(hr_token, db):
    users = db.query(User).filter(User.role.in_(["employee", "manager"])).limit(2).all()
    assert len(users) >= 2

    u1, u2 = users[0], users[1]
    resp1 = client.get(f"/api/users/{u1.id}/details", headers={"Authorization": f"Bearer {hr_token}"})
    resp2 = client.get(f"/api/users/{u2.id}/details", headers={"Authorization": f"Bearer {hr_token}"})

    assert resp1.status_code == 200
    assert resp2.status_code == 200

    d1 = resp1.json()
    d2 = resp2.json()

    assert d1["profile"]["id"] == u1.id
    assert d1["profile"]["name"] == u1.name
    assert d2["profile"]["id"] == u2.id
    assert d2["profile"]["name"] == u2.name


def test_rbac_unauthorized_access_rejected(emp_token):
    # Employee cannot access HR dashboard
    resp = client.get("/api/hr/dashboard", headers={"Authorization": f"Bearer {emp_token}"})
    assert resp.status_code in (401, 403), f"Expected 401/403 for employee on hr dashboard, got {resp.status_code}"

    # Employee cannot access HR employees list
    resp = client.get("/api/hr/employees", headers={"Authorization": f"Bearer {emp_token}"})
    assert resp.status_code in (401, 403), f"Expected 401/403 for employee on hr employees, got {resp.status_code}"
