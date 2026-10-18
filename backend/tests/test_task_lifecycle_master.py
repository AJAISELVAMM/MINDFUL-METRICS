from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, Task, TaskUnblockRequest, Notification, AuditLog
from app.security import create_token
from app.services.task_service import (
    derive_task_status_from_progress,
    check_and_block_overdue_tasks,
    create_task,
    update_task_details,
    create_unblock_request,
    requester_reply_unblock_clarification,
    hr_approve_unblock_request,
    hr_request_clarification,
    hr_reject_unblock_request,
    hr_verify_task,
    hr_request_task_changes,
)

client = TestClient(app)


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def setup_users(db):
    hr = db.query(User).filter(User.email == "test_hr_lifecycle@mindful.com").first()
    if not hr:
        hr = User(
            email="test_hr_lifecycle@mindful.com",
            name="Test HR Lifecycle",
            role="hr",
            department="HR",
            employee_code="HR-LC-01",
            password_hash="mock",
        )
        db.add(hr)

    mgr = db.query(User).filter(User.email == "test_mgr_lifecycle@mindful.com").first()
    if not mgr:
        mgr = User(
            email="test_mgr_lifecycle@mindful.com",
            name="Test Mgr Lifecycle",
            role="manager",
            department="Engineering",
            employee_code="MGR-LC-01",
            password_hash="mock",
        )
        db.add(mgr)

    emp = db.query(User).filter(User.email == "test_emp_lifecycle@mindful.com").first()
    if not emp:
        emp = User(
            email="test_emp_lifecycle@mindful.com",
            name="Test Emp Lifecycle",
            role="employee",
            department="Engineering",
            employee_code="EMP-LC-01",
            manager_name="Test Mgr Lifecycle",
            password_hash="mock",
        )
        db.add(emp)

    db.commit()
    db.refresh(hr)
    db.refresh(mgr)
    db.refresh(emp)

    yield {"hr": hr, "mgr": mgr, "emp": emp}

    # Teardown: clean up test data so real database is never polluted
    uids = [hr.id, mgr.id, emp.id]
    db.query(TaskUnblockRequest).filter(TaskUnblockRequest.requester_id.in_(uids)).delete(synchronize_session=False)
    db.query(Notification).filter(Notification.employee_id.in_(uids)).delete(synchronize_session=False)
    db.query(AuditLog).filter(AuditLog.actor_id.in_(uids)).delete(synchronize_session=False)
    db.query(Task).filter(Task.employee_id.in_(uids)).delete(synchronize_session=False)
    db.query(User).filter(User.id.in_(uids)).delete(synchronize_session=False)
    db.commit()


@pytest.fixture(scope="module")
def headers(setup_users):
    return {
        "hr": {"Authorization": f"Bearer {create_token(setup_users['hr'])}"},
        "mgr": {"Authorization": f"Bearer {create_token(setup_users['mgr'])}"},
        "emp": {"Authorization": f"Bearer {create_token(setup_users['emp'])}"},
    }


# ============================================================================
# PHASE 3: AUTOMATIC TASK STATUS MAPPING TESTS
# ============================================================================

def test_automatic_task_status_mapping():
    assert derive_task_status_from_progress(0) == "Not Started"
    assert derive_task_status_from_progress(1) == "In Progress"
    assert derive_task_status_from_progress(50) == "In Progress"
    assert derive_task_status_from_progress(75) == "In Progress"
    assert derive_task_status_from_progress(76) == "Almost Completed"
    assert derive_task_status_from_progress(90) == "Almost Completed"
    assert derive_task_status_from_progress(99) == "Almost Completed"
    assert derive_task_status_from_progress(100) == "Completed"

    # Out of range / invalid types
    with pytest.raises(ValueError):
        derive_task_status_from_progress(-1)
    with pytest.raises(ValueError):
        derive_task_status_from_progress(101)
    with pytest.raises(ValueError):
        derive_task_status_from_progress("invalid")


# ============================================================================
# PHASE 2: ROLE-BASED TASK ASSIGNMENT TESTS
# ============================================================================

def test_role_based_task_creation_permissions(db, setup_users, headers):
    emp = setup_users["emp"]
    mgr = setup_users["mgr"]
    hr = setup_users["hr"]

    # 1. Employee cannot create tasks
    res_emp = client.post(
        "/api/tasks",
        json={"name": "Employee self-assigned task", "priority": "High"},
        headers=headers["emp"],
    )
    assert res_emp.status_code == 400
    assert "Unauthorized: Employees cannot create tasks" in res_emp.json()["detail"]

    # 2. Manager cannot create tasks for themselves
    res_mgr_self = client.post(
        "/api/tasks",
        json={"name": "Manager self task", "assigned_to": mgr.id},
        headers=headers["mgr"],
    )
    assert res_mgr_self.status_code == 400
    assert "Managers cannot create tasks for themselves" in res_mgr_self.json()["detail"]

    # 3. Manager can assign task to their team member
    res_mgr_emp = client.post(
        "/api/tasks",
        json={"name": "Manager assigned task for employee", "assigned_to": emp.id, "priority": "High"},
        headers=headers["mgr"],
    )
    assert res_mgr_emp.status_code == 200
    assert res_mgr_emp.json()["status"] == "Not Started"

    # 4. HR can assign task to employee or manager
    res_hr = client.post(
        "/api/tasks",
        json={"name": "HR assigned task to Manager", "assigned_to": mgr.id, "priority": "Medium"},
        headers=headers["hr"],
    )
    assert res_hr.status_code == 200
    assert res_hr.json()["ok"] is True


# ============================================================================
# PHASE 4: COMPLETED TASK LOCK TESTS
# ============================================================================

def test_task_completion_and_locking(db, setup_users, headers):
    emp = setup_users["emp"]
    hr = setup_users["hr"]

    # Create task assigned by HR to employee
    task = Task(
        employee_id=emp.id,
        assigned_by_id=hr.id,
        assigned_by_name=hr.name,
        name="Task for Completion Lock Test",
        deadline="2026-10-30",
        due_date=date(2026, 10, 30),
        status="In Progress",
        completion_percentage=50,
        verification_status="None",
        created_at=datetime.utcnow(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Update to 100%
    res_complete = client.put(
        f"/api/tasks/T-{task.id}",
        json={"progress": 100, "work_update": "Finished all deliverables completely."},
        headers=headers["emp"],
    )
    assert res_complete.status_code == 200
    assert res_complete.json()["status"] == "Completed"
    assert res_complete.json()["progress"] == 100

    db.refresh(task)
    assert task.status == "Completed"
    assert task.completion_percentage == 100
    assert task.verification_status == "Awaiting Verification"
    assert task.completed_at is not None
    assert task.completed_by_id == emp.id

    # Verify HR notification was created
    notif = (
        db.query(Notification)
        .filter(Notification.employee_id == hr.id, Notification.title == "Task Awaiting Verification")
        .order_by(Notification.id.desc())
        .first()
    )
    assert notif is not None
    assert task.name in notif.body

    # Now attempt ordinary update to revert progress -> MUST BE REJECTED
    res_locked = client.put(
        f"/api/tasks/T-{task.id}",
        json={"progress": 50, "work_update": "Trying to reopen"},
        headers=headers["emp"],
    )
    assert res_locked.status_code == 400
    assert "Completed tasks are locked" in res_locked.json()["detail"]


# ============================================================================
# PHASE 5: AUTOMATIC DEADLINE BLOCKING TESTS
# ============================================================================

def test_automatic_deadline_blocking(db, setup_users, headers):
    emp = setup_users["emp"]
    hr = setup_users["hr"]

    # 1. Task not yet overdue
    future_task = Task(
        employee_id=emp.id,
        assigned_by_id=hr.id,
        assigned_by_name=hr.name,
        name="Future Task Not Blocked",
        deadline="2026-12-31",
        due_date=date(2026, 12, 31),
        status="In Progress",
        completion_percentage=40,
        created_at=datetime.utcnow(),
    )
    db.add(future_task)

    # 2. Incomplete task with past deadline
    past_due_date = date.today() - timedelta(days=2)
    overdue_task = Task(
        employee_id=emp.id,
        assigned_by_id=hr.id,
        assigned_by_name=hr.name,
        name="Overdue Task to be Blocked",
        deadline=str(past_due_date),
        due_date=past_due_date,
        status="In Progress",
        completion_percentage=60,
        created_at=datetime.utcnow(),
    )
    db.add(overdue_task)

    # 3. Completed task with past deadline should NEVER be blocked
    completed_past_task = Task(
        employee_id=emp.id,
        assigned_by_id=hr.id,
        assigned_by_name=hr.name,
        name="Completed Task with Past Deadline",
        deadline=str(past_due_date),
        due_date=past_due_date,
        status="Completed",
        completion_percentage=100,
        verification_status="Verified",
        completed_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(completed_past_task)
    db.commit()

    # Run check_and_block_overdue_tasks
    blocked_count = check_and_block_overdue_tasks(db)
    assert blocked_count >= 1

    db.refresh(future_task)
    db.refresh(overdue_task)
    db.refresh(completed_past_task)

    # Future task remains In Progress
    assert future_task.status == "In Progress"
    assert future_task.missed_deadline_at is None

    # Overdue task becomes Blocked
    assert overdue_task.status == "Blocked"
    assert overdue_task.missed_deadline_at is not None
    assert overdue_task.completion_percentage == 60  # progress preserved!

    # Completed past task is still Completed
    assert completed_past_task.status == "Completed"

    # Idempotence check: run again immediately -> returns 0
    second_run = check_and_block_overdue_tasks(db)
    assert second_run == 0

    # Ordinary update on blocked task is rejected
    res_blocked_update = client.put(
        f"/api/tasks/T-{overdue_task.id}",
        json={"progress": 70, "work_update": "Trying to update blocked task"},
        headers=headers["emp"],
    )
    assert res_blocked_update.status_code == 400
    assert "This task is Blocked" in res_blocked_update.json()["detail"]


# ============================================================================
# PHASE 6 & 7: UNBLOCK REQUEST & HR REVIEW WORKFLOW TESTS
# ============================================================================

def test_unblock_request_workflow(db, setup_users, headers):
    emp = setup_users["emp"]
    hr = setup_users["hr"]

    # Blocked task for unblock workflow
    task = Task(
        employee_id=emp.id,
        assigned_by_id=hr.id,
        assigned_by_name=hr.name,
        name="Blocked Task for Unblock Workflow",
        deadline="2026-10-01",
        due_date=date(2026, 10, 1),
        status="Blocked",
        completion_percentage=50,
        blocked_reason="Missed deadline on 2026-10-01",
        created_at=datetime.utcnow(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 1. Employee submits unblock request
    new_dl = str(date.today() + timedelta(days=10))
    res_req = client.post(
        f"/api/tasks/T-{task.id}/unblock-request",
        json={
            "requested_new_deadline": new_dl,
            "extension_reason": "API dependency was delayed by vendor",
            "work_completed": "Completed initial integration and models",
            "remaining_work": "End-to-end testing and documentation",
            "supporting_notes": "Vendor credentials received today",
        },
        headers=headers["emp"],
    )
    assert res_req.status_code == 200
    unblock_id = res_req.json()["id"]
    assert res_req.json()["status"] == "Pending HR Review"

    # 2. Duplicate active request is rejected
    res_dup = client.post(
        f"/api/tasks/T-{task.id}/unblock-request",
        json={
            "requested_new_deadline": new_dl,
            "extension_reason": "Duplicate request",
            "work_completed": "All",
            "remaining_work": "None",
        },
        headers=headers["emp"],
    )
    assert res_dup.status_code == 400
    assert "active unblock request is already pending" in res_dup.json()["detail"]

    # 3. HR inspects unblock requests queue
    res_queue = client.get("/api/hr/tasks/unblock-requests", headers=headers["hr"])
    assert res_queue.status_code == 200
    queue_data = res_queue.json()
    matching_req = next((r for r in queue_data if r["id"] == unblock_id), None)
    assert matching_req is not None
    assert matching_req["task_title"] == task.name
    assert matching_req["requester_name"] == emp.name
    assert matching_req["status"] == "Pending HR Review"

    # 4. HR asks for clarification
    res_clarify = client.post(
        f"/api/hr/tasks/unblock-requests/{unblock_id}/clarify",
        json={"message": "Please confirm test plan and QA sign-off date."},
        headers=headers["hr"],
    )
    assert res_clarify.status_code == 200
    assert res_clarify.json()["status"] == "More Information Required"

    # 5. Requester provides clarification response
    res_reply = client.post(
        f"/api/tasks/unblock-requests/{unblock_id}/reply",
        json={"response": "QA sign-off scheduled for 24 Oct, test suite prepared."},
        headers=headers["emp"],
    )
    assert res_reply.status_code == 200
    assert res_reply.json()["status"] == "Pending HR Review"

    # 6. HR approves extension and unblocks task
    res_approve = client.post(
        f"/api/hr/tasks/unblock-requests/{unblock_id}/approve",
        json={"reason": "Approved extension after QA schedule confirmed"},
        headers=headers["hr"],
    )
    assert res_approve.status_code == 200
    assert res_approve.json()["status"] == "Approved"

    # Verify task is unblocked and status derived from progress (50% -> In Progress)
    db.refresh(task)
    assert task.status == "In Progress"
    assert task.deadline == new_dl
    assert task.blocked_reason is None
    assert task.completion_percentage == 50

    # Task is now unblocked and can be updated normally!
    res_upd = client.put(
        f"/api/tasks/T-{task.id}",
        json={"progress": 75, "work_update": "Integration complete, starting tests"},
        headers=headers["emp"],
    )
    assert res_upd.status_code == 200
    assert res_upd.json()["status"] == "In Progress"


def test_unblock_rejection(db, setup_users, headers):
    emp = setup_users["emp"]
    hr = setup_users["hr"]

    task = Task(
        employee_id=emp.id,
        assigned_by_id=hr.id,
        assigned_by_name=hr.name,
        name="Task for Unblock Rejection Test",
        deadline="2026-10-05",
        due_date=date(2026, 10, 5),
        status="Blocked",
        completion_percentage=10,
        blocked_reason="Missed deadline",
        created_at=datetime.utcnow(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    req = TaskUnblockRequest(
        task_id=task.id,
        requester_id=emp.id,
        requester_role=emp.role,
        original_deadline=task.deadline,
        requested_new_deadline="2026-11-01",
        extension_reason="Need more time",
        work_completed="10%",
        remaining_work="90%",
        status="Pending HR Review",
        created_at=datetime.utcnow(),
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    # HR rejects
    res_rej = client.post(
        f"/api/hr/tasks/unblock-requests/{req.id}/reject",
        json={"reason": "Insufficient justification for 1-month delay"},
        headers=headers["hr"],
    )
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "Rejected"

    db.refresh(task)
    assert task.status == "Blocked"  # remains blocked!


# ============================================================================
# PHASE 8: HR TASK VERIFICATION WORKFLOW TESTS
# ============================================================================

def test_hr_task_verification_workflow(db, setup_users, headers):
    emp = setup_users["emp"]
    hr = setup_users["hr"]

    # 1. Create a task that reaches 100%
    task = Task(
        employee_id=emp.id,
        assigned_by_id=hr.id,
        assigned_by_name=hr.name,
        name="Task for HR Verification Queue Test",
        deadline="2026-10-25",
        due_date=date(2026, 10, 25),
        status="Completed",
        completion_percentage=100,
        completed_at=datetime.utcnow(),
        completed_by_id=emp.id,
        verification_status="Awaiting Verification",
        work_update="All modules delivered and unit tests passing 100%",
        created_at=datetime.utcnow(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 2. Appears in HR verification queue
    res_vqueue = client.get("/api/hr/tasks/verification-queue", headers=headers["hr"])
    assert res_vqueue.status_code == 200
    vqueue_data = res_vqueue.json()
    item = next((t for t in vqueue_data if t["raw_id"] == task.id), None)
    assert item is not None
    assert item["verification_status"] == "Awaiting Verification"
    assert item["progress"] == 100

    # 3. Non-HR cannot verify (HTTP 403)
    res_unauth = client.post(
        f"/api/hr/tasks/T-{task.id}/verify",
        json={"notes": "Unauthorized attempt"},
        headers=headers["emp"],
    )
    assert res_unauth.status_code == 403

    # 4. HR verifies task
    res_verify = client.post(
        f"/api/hr/tasks/T-{task.id}/verify",
        json={"notes": "Code quality and deliverables verified by Senior Architect"},
        headers=headers["hr"],
    )
    assert res_verify.status_code == 200
    assert res_verify.json()["verification_status"] == "Verified"

    db.refresh(task)
    assert task.verification_status == "Verified"
    assert task.verified_by_id == hr.id
    assert task.verified_at is not None
    assert task.status == "Completed"

    # Notification sent to task owner
    owner_notif = (
        db.query(Notification)
        .filter(Notification.employee_id == emp.id, Notification.title == "Task Verified by HR")
        .order_by(Notification.id.desc())
        .first()
    )
    assert owner_notif is not None


def test_hr_request_task_changes(db, setup_users, headers):
    emp = setup_users["emp"]
    hr = setup_users["hr"]

    task = Task(
        employee_id=emp.id,
        assigned_by_id=hr.id,
        assigned_by_name=hr.name,
        name="Task Needing Revisions",
        deadline="2026-10-25",
        status="Completed",
        completion_percentage=100,
        completed_at=datetime.utcnow(),
        verification_status="Awaiting Verification",
        created_at=datetime.utcnow(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # HR requests changes
    res_changes = client.post(
        f"/api/hr/tasks/T-{task.id}/request-changes",
        json={"notes": "Please add unit test coverage for edge cases."},
        headers=headers["hr"],
    )
    assert res_changes.status_code == 200
    assert res_changes.json()["verification_status"] == "Changes Requested"
    assert res_changes.json()["status"] == "In Progress"
    assert res_changes.json()["progress"] == 90

    db.refresh(task)
    assert task.verification_status == "Changes Requested"
    assert task.status == "In Progress"
    assert task.completion_percentage == 90


# ============================================================================
# PHASE 9 & 15: WORKLOAD & DONUT CHART CONSISTENCY TESTS
# ============================================================================

def test_workload_and_chart_center_count(db, setup_users, headers):
    emp = setup_users["emp"]

    res_work = client.get("/api/tasks/my", headers=headers["emp"])
    assert res_work.status_code == 200
    data = res_work.json()

    summary = data["summary"]
    tasks = data["tasks"]

    # Donut center assigned total equals tasks length
    assert summary["assigned"] == len(tasks)

    # Sum of categories
    completed = summary["completed"]
    almost_completed = summary.get("almost_completed", 0)
    in_progress = summary["in_progress"]
    not_started = summary["not_started"]
    blocked = summary["blocked"]

    assert completed + almost_completed + in_progress + not_started + blocked <= summary["assigned"]
    assert summary["completion"] == round(100 * completed / max(len(tasks), 1))
