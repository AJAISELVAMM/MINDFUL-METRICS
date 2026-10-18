from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import (
    User, Task, TaskUnblockRequest, Notification, AuditLog, Prediction,
    BurnoutFeatures, Communication, Attendance, LeaveRequest
)
from app.security import create_token

client = TestClient(app)


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def setup_test_actors(db):
    # HR User
    hr = db.query(User).filter(User.email == "test_hr_wf@mindful.com").first()
    if not hr:
        hr = User(
            name="HR Workflows Reviewer",
            email="test_hr_wf@mindful.com",
            password_hash="test_pw_hash",
            employee_code="HR-WF-01",
            role="hr",
            department="Human Resources",
        )
        db.add(hr)

    # Manager User
    mgr = db.query(User).filter(User.email == "test_mgr_wf@mindful.com").first()
    if not mgr:
        mgr = User(
            name="Manager Workflow Lead",
            email="test_mgr_wf@mindful.com",
            password_hash="test_pw_hash",
            employee_code="MGR-WF-01",
            role="manager",
            department="Platform Engineering",
        )
        db.add(mgr)

    # Employee A
    emp_a = db.query(User).filter(User.email == "test_emp_a_wf@mindful.com").first()
    if not emp_a:
        emp_a = User(
            name="Employee Alpha",
            email="test_emp_a_wf@mindful.com",
            password_hash="test_pw_hash",
            employee_code="EMP-A-01",
            role="employee",
            department="Platform Engineering",
            manager_name="Manager Workflow Lead",
        )
        db.add(emp_a)

    # Employee B
    emp_b = db.query(User).filter(User.email == "test_emp_b_wf@mindful.com").first()
    if not emp_b:
        emp_b = User(
            name="Employee Beta",
            email="test_emp_b_wf@mindful.com",
            password_hash="test_pw_hash",
            employee_code="EMP-B-02",
            role="employee",
            department="Security Engineering",
            manager_name="Other Manager",
        )
        db.add(emp_b)

    db.commit()
    db.refresh(hr)
    db.refresh(mgr)
    db.refresh(emp_a)
    db.refresh(emp_b)

    mgr.manager_id = hr.id
    emp_a.manager_id = mgr.id
    db.commit()

    hr_token = create_token(hr)
    mgr_token = create_token(mgr)
    emp_a_token = create_token(emp_a)
    emp_b_token = create_token(emp_b)

    yield {
        "hr": hr,
        "mgr": mgr,
        "emp_a": emp_a,
        "emp_b": emp_b,
        "hr_token": hr_token,
        "mgr_token": mgr_token,
        "emp_a_token": emp_a_token,
        "emp_b_token": emp_b_token,
    }

    # Teardown: clean up test entities
    uids = [hr.id, mgr.id, emp_a.id, emp_b.id]
    db.query(TaskUnblockRequest).filter((TaskUnblockRequest.requester_id.in_(uids)) | (TaskUnblockRequest.reviewed_by_id.in_(uids))).delete(synchronize_session=False)
    db.query(Notification).filter(Notification.employee_id.in_(uids)).delete(synchronize_session=False)
    db.query(AuditLog).filter(AuditLog.actor_id.in_(uids)).delete(synchronize_session=False)
    db.query(Prediction).filter(Prediction.employee_id.in_(uids)).delete(synchronize_session=False)
    db.query(BurnoutFeatures).filter(BurnoutFeatures.employee_id.in_(uids)).delete(synchronize_session=False)
    db.query(Communication).filter(Communication.employee_id.in_(uids)).delete(synchronize_session=False)
    db.query(Task).filter((Task.employee_id.in_(uids)) | (Task.assigned_by_id.in_(uids))).delete(synchronize_session=False)
    db.query(User).filter(User.manager_id.in_(uids)).update({"manager_id": None}, synchronize_session=False)
    db.query(User).filter(User.id.in_(uids)).delete(synchronize_session=False)
    db.commit()


def test_issue2_ask_for_details_workflow(db, setup_test_actors):
    """
    ISSUE 2:
    - Empty clarification is rejected.
    - Valid clarification persists in PostgreSQL.
    - Status becomes 'More Information Required'.
    - Task remains 'Blocked'.
    - Requester can view and respond.
    - Response persists and returns request to 'Pending HR Review'.
    - HR receives notification.
    """
    actors = setup_test_actors
    emp_a = actors["emp_a"]
    hr = actors["hr"]

    # 1. Create a blocked task for emp_a
    task = Task(
        name="Backend Auth Migration",
        employee_id=emp_a.id,
        status="Blocked",
        completion_percentage=40,
        deadline="2026-03-01",
        blocked_reason="Missing OAuth client credentials",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 2. Submit an unblock request
    unblock = TaskUnblockRequest(
        task_id=task.id,
        requester_id=emp_a.id,
        requester_role="employee",
        original_deadline=task.deadline,
        requested_new_deadline="2026-03-15",
        blocking_reason=task.blocked_reason,
        extension_reason="Waiting on platform team secrets",
        work_completed="Scaffolded OAuth handlers",
        remaining_work="End-to-end integration tests",
        status="Pending HR Review",
    )
    db.add(unblock)
    db.commit()
    db.refresh(unblock)

    # 3. HR asks for details with EMPTY message -> Must fail with 400
    res_empty = client.post(
        f"/api/hr/tasks/unblock-requests/{unblock.id}/clarify",
        headers={"Authorization": f"Bearer {actors['hr_token']}"},
        json={"message": "   "},
    )
    assert res_empty.status_code == 400
    assert "clarification message is required" in res_empty.json()["detail"].lower()

    # 4. HR submits valid clarification
    res_valid = client.post(
        f"/api/hr/tasks/unblock-requests/{unblock.id}/clarify",
        headers={"Authorization": f"Bearer {actors['hr_token']}"},
        json={"message": "Please confirm which third-party OAuth provider is holding this up."},
    )
    assert res_valid.status_code == 200
    data = res_valid.json()
    assert data["ok"] is True
    assert data["status"] == "More Information Required"
    assert "third-party OAuth provider" in data["clarification_requested"]

    # Verify database persistence
    db.expire_all()
    reloaded_unblock = db.query(TaskUnblockRequest).filter(TaskUnblockRequest.id == unblock.id).first()
    assert reloaded_unblock.status == "More Information Required"
    assert reloaded_unblock.reviewed_by_id == hr.id
    assert reloaded_unblock.clarification_requested_at is not None

    # Verify task remains Blocked with unchanged deadline
    reloaded_task = db.query(Task).filter(Task.id == task.id).first()
    assert reloaded_task.status == "Blocked"
    assert reloaded_task.deadline == "2026-03-01"

    # Verify requester notification
    notif = (
        db.query(Notification)
        .filter(Notification.employee_id == emp_a.id)
        .order_by(Notification.id.desc())
        .first()
    )
    assert notif is not None
    assert "More Information Required" in notif.title

    # 5. Unauthorized employee B tries to reply -> Must fail with 400/403
    res_unauth = client.post(
        f"/api/tasks/unblock-requests/{unblock.id}/reply",
        headers={"Authorization": f"Bearer {actors['emp_b_token']}"},
        json={"response": "Unauthorized intruder answering."},
    )
    assert res_unauth.status_code in (400, 403)

    # 6. Original requester emp_a replies with empty message -> Must fail
    res_emp_empty = client.post(
        f"/api/tasks/unblock-requests/{unblock.id}/reply",
        headers={"Authorization": f"Bearer {actors['emp_a_token']}"},
        json={"response": "   "},
    )
    assert res_emp_empty.status_code == 400

    # 7. Original requester emp_a submits valid clarification response
    res_emp_reply = client.post(
        f"/api/tasks/unblock-requests/{unblock.id}/reply",
        headers={"Authorization": f"Bearer {actors['emp_a_token']}"},
        json={"response": "It is GitHub enterprise OAuth; awaiting admin approval for client ID."},
    )
    assert res_emp_reply.status_code == 200
    reply_data = res_emp_reply.json()
    assert reply_data["status"] == "Pending HR Review"
    assert "GitHub enterprise OAuth" in reply_data["clarification_response"]

    # Verify DB persistence and HR notification
    db.expire_all()
    reloaded_unblock2 = db.query(TaskUnblockRequest).filter(TaskUnblockRequest.id == unblock.id).first()
    assert reloaded_unblock2.status == "Pending HR Review"
    assert reloaded_unblock2.clarification_responded_at is not None

    hr_notif = (
        db.query(Notification)
        .filter(Notification.employee_id == hr.id)
        .order_by(Notification.id.desc())
        .first()
    )
    assert hr_notif is not None
    assert "Clarification Provided" in hr_notif.title


def test_issue3_request_changes_and_reverification_workflow(db, setup_test_actors):
    """
    ISSUE 3:
    - Missing feedback is rejected.
    - Valid feedback persists with HR ID and timestamp.
    - Verification status becomes 'Changes Requested'.
    - Task reopened to In Progress (90%).
    - Owner can review feedback and submit corrected work (100%).
    - Task returns to 'Awaiting Verification'.
    - Never incorrectly marks Verified when changes requested.
    """
    actors = setup_test_actors
    emp_a = actors["emp_a"]
    hr = actors["hr"]

    # 1. Create a completed task awaiting verification
    task = Task(
        name="Security Audit Compliance Report",
        employee_id=emp_a.id,
        status="Completed",
        completion_percentage=100,
        deadline="2026-12-31",
        verification_status="Awaiting Verification",
        work_update="Completed draft security controls audit.",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 2. HR attempts to request changes with EMPTY feedback -> Must fail with 400
    res_empty = client.post(
        f"/api/hr/tasks/T-{task.id}/request-changes",
        headers={"Authorization": f"Bearer {actors['hr_token']}"},
        json={"notes": "   "},
    )
    assert res_empty.status_code == 400
    assert "provide an explanation" in res_empty.json()["detail"].lower()

    # 3. HR submits valid changes request
    feedback = "Please add Appendix B with vulnerability scan logs before signoff."
    res_valid = client.post(
        f"/api/hr/tasks/T-{task.id}/request-changes",
        headers={"Authorization": f"Bearer {actors['hr_token']}"},
        json={"notes": feedback},
    )
    assert res_valid.status_code == 200
    data = res_valid.json()
    assert data["verification_status"] == "Changes Requested"
    assert data["status"] == "In Progress"
    assert data["progress"] == 90

    # Verify task state in database
    db.expire_all()
    reloaded = db.query(Task).filter(Task.id == task.id).first()
    assert reloaded.verification_status == "Changes Requested"
    assert reloaded.verification_notes == feedback
    assert reloaded.status == "In Progress"
    assert reloaded.completion_percentage == 90

    # Owner notification
    notif = (
        db.query(Notification)
        .filter(Notification.employee_id == emp_a.id)
        .order_by(Notification.id.desc())
        .first()
    )
    assert notif is not None
    assert "Changes Requested" in notif.title

    # 4. Owner resubmits corrected work (progress = 100%)
    res_resubmit = client.patch(
        f"/api/tasks/T-{task.id}",
        headers={"Authorization": f"Bearer {actors['emp_a_token']}"},
        json={
            "progress": 100,
            "work_update": "Appended full Appendix B with clean vulnerability scan logs as requested.",
        },
    )
    assert res_resubmit.status_code == 200
    resub_data = res_resubmit.json()
    assert resub_data["status"] == "Completed"
    assert resub_data["verification_status"] == "Awaiting Verification"

    # Verify HR notification of resubmission
    db.expire_all()
    hr_resub_notif = (
        db.query(Notification)
        .filter(Notification.employee_id == hr.id)
        .order_by(Notification.id.desc())
        .first()
    )
    assert hr_resub_notif is not None
    assert "Corrected Task Resubmitted" in hr_resub_notif.title


def test_issue4_selected_person_data_isolation(db, setup_test_actors):
    """
    ISSUE 4:
    - Verify 2 different employees (emp_a, emp_b) and 1 manager (mgr) with intentionally distinct data.
    - Each user's details endpoint returns exactly their data.
    - Emp A's task count matches Emp A's task records.
    - Emp B's task count matches Emp B's task records.
    - Manager's personal task count does not mix with team tasks.
    - Missing/invalid IDs return 404 (never substitute another person).
    - Unauthorized access between employees is rejected (403).
    """
    actors = setup_test_actors
    emp_a = actors["emp_a"]
    emp_b = actors["emp_b"]
    mgr = actors["mgr"]
    hr = actors["hr"]

    # Give Emp A 3 distinct tasks
    for i in range(3):
        db.add(Task(
            name=f"Alpha Personal Task {i+1}",
            employee_id=emp_a.id,
            status="In Progress" if i < 2 else "Completed",
            completion_percentage=50 if i < 2 else 100,
        ))

    # Give Emp B 5 distinct tasks
    for i in range(5):
        db.add(Task(
            name=f"Beta Security Task {i+1}",
            employee_id=emp_b.id,
            status="Blocked" if i == 0 else "In Progress",
            completion_percentage=20,
            blocked_reason="Firewall approval pending" if i == 0 else None,
        ))

    # Give Manager 1 personal task and 4 team tasks assigned by manager
    db.add(Task(
        name="Manager Personal Strategic Plan",
        employee_id=mgr.id,
        status="In Progress",
        completion_percentage=60,
    ))
    for i in range(4):
        db.add(Task(
            name=f"Team Project Task {i+1}",
            employee_id=emp_a.id,
            assigned_by_id=mgr.id,
            status="In Progress",
            completion_percentage=30,
        ))

    # Give Emp A distinct Burnout Prediction (42 - Moderate)
    db.add(Prediction(
        employee_id=emp_a.id,
        burnout_score=42.0,
        risk_level="Moderate",
        top_factors=[{"name": "Workload Volatility", "importance": 0.4}],
        recommendations=["Take structured breaks during sprint peaks"],
    ))

    # Give Emp B distinct Burnout Prediction (78 - High)
    db.add(Prediction(
        employee_id=emp_b.id,
        burnout_score=78.0,
        risk_level="High",
        top_factors=[{"name": "Overtime Frequency", "importance": 0.7}],
        recommendations=["Mandatory workload reduction review"],
    ))

    # Give Mgr distinct Burnout Prediction (25 - Low)
    db.add(Prediction(
        employee_id=mgr.id,
        burnout_score=25.0,
        risk_level="Low",
        top_factors=[{"name": "Balanced Schedule", "importance": 0.2}],
        recommendations=["Maintain current routine"],
    ))

    db.commit()

    # 1. HR requests Emp A details
    res_a = client.get(
        f"/api/users/{emp_a.id}/details",
        headers={"Authorization": f"Bearer {actors['hr_token']}"},
    )
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["profile"]["name"] == emp_a.name
    assert data_a["profile"]["employee_id"] == emp_a.employee_code
    assert data_a["wellbeing"]["burnout_score"] == 42
    assert data_a["wellbeing"]["risk_level"] == "Moderate"
    # Task count must match Emp A's personal tasks (3 created + 4 assigned by mgr + 1 from test 2 + 1 from test 3 = 9)
    emp_a_db_tasks = db.query(Task).filter(Task.employee_id == emp_a.id).count()
    assert data_a["workload"]["total_tasks"] == emp_a_db_tasks
    assert len(data_a["tasks"]) == emp_a_db_tasks

    # 2. HR requests Emp B details
    res_b = client.get(
        f"/api/users/{emp_b.id}/details",
        headers={"Authorization": f"Bearer {actors['hr_token']}"},
    )
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["profile"]["name"] == emp_b.name
    assert data_b["profile"]["employee_id"] == emp_b.employee_code
    assert data_b["wellbeing"]["burnout_score"] == 78
    assert data_b["wellbeing"]["risk_level"] == "High"
    assert data_b["workload"]["blocked_tasks"] >= 1
    emp_b_db_tasks = db.query(Task).filter(Task.employee_id == emp_b.id).count()
    assert data_b["workload"]["total_tasks"] == emp_b_db_tasks
    # Ensure Emp A and Emp B data are strictly isolated and not mixed
    assert data_a["wellbeing"]["burnout_score"] != data_b["wellbeing"]["burnout_score"]
    assert data_a["profile"]["email"] != data_b["profile"]["email"]

    # 3. HR requests Manager C details
    res_mgr = client.get(
        f"/api/users/{mgr.id}/details",
        headers={"Authorization": f"Bearer {actors['hr_token']}"},
    )
    assert res_mgr.status_code == 200
    data_mgr = res_mgr.json()
    assert data_mgr["profile"]["name"] == mgr.name
    assert data_mgr["wellbeing"]["burnout_score"] == 25
    # Manager personal tasks should ONLY count tasks assigned TO the manager, NOT the team tasks
    mgr_personal_tasks = db.query(Task).filter(Task.employee_id == mgr.id).count()
    assert data_mgr["workload"]["total_tasks"] == mgr_personal_tasks
    assert data_mgr["team_stats"] is not None
    assert data_mgr["team_stats"]["team_tasks_count"] >= 4
    assert data_mgr["workload"]["total_tasks"] < (mgr_personal_tasks + data_mgr["team_stats"]["team_tasks_count"])

    # 4. Query by alphanumeric employee_code (string resolution)
    res_code = client.get(
        f"/api/users/{emp_b.employee_code}/details",
        headers={"Authorization": f"Bearer {actors['hr_token']}"},
    )
    assert res_code.status_code == 200
    assert res_code.json()["profile"]["name"] == emp_b.name

    # 5. Nonexistent user ID returns 404
    res_404 = client.get(
        "/api/users/NON_EXISTENT_999999/details",
        headers={"Authorization": f"Bearer {actors['hr_token']}"},
    )
    assert res_404.status_code == 404

    # 6. Unauthorized access check: Emp A cannot view Emp B's details
    res_unauth = client.get(
        f"/api/users/{emp_b.id}/details",
        headers={"Authorization": f"Bearer {actors['emp_a_token']}"},
    )
    assert res_unauth.status_code == 403
