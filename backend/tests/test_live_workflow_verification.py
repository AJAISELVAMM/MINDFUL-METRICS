from __future__ import annotations
import pytest
from datetime import date, datetime
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, Attendance, Task, Survey, Prediction, BurnoutFeatures
from app.security import create_token
from app.ml.feature_engineering import FEATURE_ORDER
from app.ml.model_loader import load_joblib, load_metadata

client = TestClient(app)


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def emp_user(db):
    user = db.query(User).filter(User.role == "employee").first()
    assert user is not None, "No employee found in database"
    return user


@pytest.fixture(scope="module")
def mgr_user(db):
    user = db.query(User).filter(User.role == "manager").first()
    assert user is not None, "No manager found in database"
    return user


@pytest.fixture(scope="module")
def hr_user(db):
    user = db.query(User).filter(User.role == "hr").first()
    assert user is not None, "No HR user found in database"
    return user


@pytest.fixture
def emp_headers(emp_user):
    token = create_token(emp_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mgr_headers(mgr_user):
    token = create_token(mgr_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def hr_headers(hr_user):
    token = create_token(hr_user)
    return {"Authorization": f"Bearer {token}"}


# ===============================================================
# A. EMPLOYEE CHECK-IN WORKFLOW
# ===============================================================

def test_employee_checkin_with_survey(emp_headers, emp_user, db):
    # Submit morning survey questions together with check-in
    morning_answers = {
        "stress": 3,
        "energy": 4,
        "manageable": 4,
        "satisfied": 4,
        "wlb": 3,
        "deadline": 2,
        "difficulty": 3,
        "overtime": 1,
    }

    # First test check-in survey endpoint standalone
    res_survey = client.post(
        "/api/survey/daily?survey_type=morning",
        json={"answers": morning_answers, "note": "Feeling energetic and ready for sprints today."},
        headers=emp_headers,
    )
    assert res_survey.status_code == 200
    survey_data = res_survey.json()
    assert survey_data.get("ok") is True
    assert "prediction" in survey_data
    assert "burnout_score" in survey_data["prediction"]

    # Verify survey is saved in DB
    today_d = date.today()
    saved_survey = (
        db.query(Survey)
        .filter(Survey.employee_id == emp_user.id, Survey.date == today_d, Survey.survey_type == "morning")
        .first()
    )
    assert saved_survey is not None
    assert saved_survey.answers.get("stress") == 3

    # Check-in API call
    res_checkin = client.post(
        "/api/attendance/check-in",
        json={"answers": morning_answers},
        headers=emp_headers,
    )
    # Status code is either 200 (checked in) or 400 (already checked in today)
    assert res_checkin.status_code in (200, 400)
    if res_checkin.status_code == 200:
        data = res_checkin.json()
        assert data.get("ok") is True
        assert "time" in data
        assert "status" in data
        assert "prediction" in data


# ===============================================================
# B. EMPLOYEE CHECK-OUT WORKFLOW
# ===============================================================

def test_employee_checkout_with_survey(emp_headers, emp_user, db):
    evening_answers = {
        "workload": 4,
        "stress": 2,
        "energyLeft": 3,
        "satisfied": 4,
        "deadline": 2,
        "difficulty": 3,
        "exhausted": 2,
    }

    # Standalone evening survey endpoint
    res_survey = client.post(
        "/api/survey/daily?survey_type=evening",
        json={"answers": evening_answers, "note": "Completed planned tasks successfully."},
        headers=emp_headers,
    )
    assert res_survey.status_code == 200
    assert res_survey.json().get("ok") is True

    # Checkout call
    res_checkout = client.post(
        "/api/attendance/check-out",
        json={"answers": evening_answers, "note": "End of day reflection."},
        headers=emp_headers,
    )
    assert res_checkout.status_code in (200, 400)


# ===============================================================
# C. MANAGER PERSONAL SCORE AND ROLE SEPARATION
# ===============================================================

def test_manager_survey_and_personal_isolation(mgr_headers, mgr_user, emp_user, db):
    # Manager survey questions include wellbeing, work, and management
    res_q = client.get("/api/survey/questions", headers=mgr_headers)
    assert res_q.status_code == 200
    q_data = res_q.json()
    assert "management" in q_data
    assert "wellbeing" in q_data

    # Manager submits their own manager survey
    mgr_answers = {
        "stress": 2,
        "energy": 4,
        "wlb": 4,
        "team_workload": 3,
        "personal_workload": 3,
        "meeting_load": 2,
    }
    res_sub = client.post(
        "/api/survey/daily?survey_type=manager",
        json={"answers": mgr_answers},
        headers=mgr_headers,
    )
    assert res_sub.status_code == 200
    mgr_pred = res_sub.json().get("prediction")
    assert mgr_pred is not None

    # Manager's personal features in DB only belong to manager_user.id
    today_d = date.today()
    mgr_bf = (
        db.query(BurnoutFeatures)
        .filter(BurnoutFeatures.employee_id == mgr_user.id, BurnoutFeatures.date == today_d)
        .first()
    )
    if mgr_bf:
        # Check that it recorded manager's own features
        assert isinstance(mgr_bf.features, dict)
        assert len(mgr_bf.features) == 21


# ===============================================================
# D. TASK UPDATES TRIGGER REAL MODEL RECOMPUTATION
# ===============================================================

def test_task_mutations_recalculate_risk(emp_headers, emp_user, mgr_headers, db):
    task_id = None
    block_task_id = None
    try:
        # Create a task for the employee via authorized manager
        res_create = client.post(
            "/api/tasks",
            json={
                "name": "Audit Security Policies",
                "priority": "High",
                "deadline": "Today",
                "difficulty": 4,
                "assigned_to": emp_user.employee_code or emp_user.id,
            },
            headers=mgr_headers,
        )
        assert res_create.status_code == 200
        task_id = res_create.json()["id"]

        # 1. Progress increase to 50%
        res_up1 = client.patch(
            f"/api/tasks/{task_id}",
            json={"progress": 50, "status": "In Progress"},
            headers=emp_headers,
        )
        assert res_up1.status_code == 200
        data1 = res_up1.json()
        assert data1["progress"] == 50
        assert data1["status"] == "In Progress"
        assert "prediction" in data1
        assert "burnout_score" in data1["prediction"]

        # 2. Complete task (100% progress)
        res_comp = client.patch(
            f"/api/tasks/{task_id}",
            json={"status": "Completed", "progress": 100},
            headers=emp_headers,
        )
        assert res_comp.status_code == 200
        data_comp = res_comp.json()
        assert data_comp["status"] == "Completed"
        assert data_comp["progress"] == 100
        assert "prediction" in data_comp

        # 3. Mark task as Blocked with blocker reason
        res_block_task = client.post(
            "/api/tasks",
            json={
                "name": "Database Schema Hotfix",
                "priority": "Medium",
                "deadline": "Tomorrow",
                "assigned_to": emp_user.employee_code or emp_user.id,
            },
            headers=mgr_headers,
        )
        assert res_block_task.status_code == 200
        block_task_id = res_block_task.json()["id"]

        res_block = client.patch(
            f"/api/tasks/{block_task_id}",
            json={"status": "Blocked", "blocked_reason": "Waiting for third-party API approval"},
            headers=emp_headers,
        )
        assert res_block.status_code == 200
        data_block = res_block.json()
        assert data_block["status"] == "Blocked"
        assert data_block["blocked_reason"] == "Waiting for third-party API approval"
        assert "prediction" in data_block
    finally:
        if task_id:
            raw_id = int(str(task_id).replace("T-", ""))
            db.query(Task).filter(Task.id == raw_id).delete()
        if block_task_id:
            raw_b_id = int(str(block_task_id).replace("T-", ""))
            db.query(Task).filter(Task.id == raw_b_id).delete()
        db.commit()


# ===============================================================
# E. ALL 21 FEATURES AND MODEL CORRECTNESS
# ===============================================================

def test_all_21_features_exact_order():
    meta = load_metadata()
    expected_order = meta.get("feature_order", [])
    assert len(expected_order) == 21
    assert expected_order == FEATURE_ORDER

    # Verify each feature exists in FEATURE_ORDER
    required_21 = [
        "stress_score",
        "workload_score",
        "work_life_balance_score",
        "energy_score",
        "mood_score",
        "job_satisfaction_score",
        "working_hours",
        "overtime_hours",
        "attendance_rate",
        "leave_frequency",
        "task_completion_rate",
        "deadline_pressure",
        "task_difficulty",
        "workload_deviation",
        "working_hour_deviation",
        "communication_sentiment",
        "communication_stress_score",
        "communication_negative_score",
        "sem_mean",
        "sem_std",
        "sem_norm",
    ]
    for feat in required_21:
        assert feat in FEATURE_ORDER, f"Missing feature: {feat}"


def test_random_forest_model_predict_contract():
    import pandas as pd
    from app.ml.feature_engineering import assemble_matrix, employee_feature_dict
    from app.ml.burnout_model import score_from_proba

    clf = load_joblib("burnout_random_forest.joblib")
    assert clf is not None

    feat = employee_feature_dict(
        stress=65,
        workload=70,
        wlb=40,
        energy=45,
        mood=45,
        hours=9.5,
        overtime=2.0,
        attendance=90,
    )
    X = assemble_matrix(pd.DataFrame([feat]))
    assert list(X.columns) == FEATURE_ORDER

    proba = clf.predict_proba(X)[0]
    score, level, probs, conf = score_from_proba(list(clf.classes_), proba)

    assert 0 <= score <= 100
    assert level in ("LOW", "MODERATE", "HIGH")
    if score <= 39:
        assert level == "LOW"
    elif score <= 69:
        assert level == "MODERATE"
    else:
        assert level == "HIGH"


# ===============================================================
# F. SECURITY AND PRIVACY ENFORCEMENT
# ===============================================================

def test_security_rbac(emp_headers, mgr_headers, hr_headers, db):
    # Employee cannot access HR dashboard
    res_hr_by_emp = client.get("/api/hr/dashboard", headers=emp_headers)
    assert res_hr_by_emp.status_code == 403

    # Employee cannot access manager team tasks
    res_team_by_emp = client.get("/api/tasks/team", headers=emp_headers)
    assert res_team_by_emp.status_code == 403

    # Invalid token rejected
    res_bad = client.get("/api/attendance/today", headers={"Authorization": "Bearer invalid.token.xyz"})
    assert res_bad.status_code == 401

    # Missing token rejected
    res_no = client.get("/api/attendance/today")
    assert res_no.status_code == 401


# ===============================================================
# G. REGRESSION TESTS
# ===============================================================

def test_health_and_core_dashboards(emp_headers, mgr_headers, hr_headers):
    # Health
    res_h = client.get("/api/health")
    assert res_h.status_code == 200
    assert res_h.json().get("ok") is True

    # Employee dashboard
    res_emp = client.get("/api/employee/dashboard", headers=emp_headers)
    assert res_emp.status_code == 200
    assert "kpis" in res_emp.json()

    # Manager dashboard
    res_mgr = client.get("/api/manager/dashboard", headers=mgr_headers)
    assert res_mgr.status_code == 200

    # HR dashboard
    res_hr = client.get("/api/hr/dashboard", headers=hr_headers)
    assert res_hr.status_code == 200
