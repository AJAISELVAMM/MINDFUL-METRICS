from __future__ import annotations
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models import User, Notification
from app.security import create_token
from app.services.notification_service import create_notification, get_unread_count

client = TestClient(app)

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture(scope="module")
def test_users(db: Session):
    emp = db.query(User).filter(User.role == "employee").first()
    mgr = db.query(User).filter(User.role == "manager").first()
    hr = db.query(User).filter(User.role == "hr").first()
    other_emp = db.query(User).filter(User.role == "employee", User.id != emp.id).first()
    return {"emp": emp, "mgr": mgr, "hr": hr, "other_emp": other_emp}

def test_1_employee_mark_notification_as_read(db: Session, test_users):
    emp = test_users["emp"]
    token = create_token(emp)

    # Create a fresh unread notification
    notif = create_notification(
        db=db,
        recipient_id=emp.id,
        title="Task Update Test",
        body="Your task has been updated",
        notification_type="TASK_PROGRESS",
        priority="normal",
        link_url="/employee/tasks",
    )
    db.commit()
    assert notif.id is not None
    initial_unread = get_unread_count(db, emp)

    # 1. Call mark as read API
    resp = client.post(
        f"/api/notifications/{notif.id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["id"] == notif.id
    assert data["is_read"] is True
    assert data["unread"] is False

    # 2. Check unread count decreased by exactly one
    new_unread = get_unread_count(db, emp)
    assert new_unread == initial_unread - 1

    # 3. Clean up
    db.query(Notification).filter(Notification.id == notif.id).delete()
    db.commit()

def test_2_mark_read_is_idempotent_no_double_decrement(db: Session, test_users):
    emp = test_users["emp"]
    token = create_token(emp)

    notif = create_notification(
        db=db,
        recipient_id=emp.id,
        title="Idempotency Test",
        body="Checking idempotency",
    )
    db.commit()

    # First mark as read
    r1 = client.post(
        f"/api/notifications/{notif.id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 200
    unread_after_first = get_unread_count(db, emp)

    # Second mark as read (already read)
    r2 = client.post(
        f"/api/notifications/{notif.id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    unread_after_second = get_unread_count(db, emp)

    # Count must NOT decrease again
    assert unread_after_second == unread_after_first

    db.query(Notification).filter(Notification.id == notif.id).delete()
    db.commit()

def test_3_refresh_preserves_persisted_read_status(db: Session, test_users):
    emp = test_users["emp"]
    token = create_token(emp)

    notif = create_notification(
        db=db,
        recipient_id=emp.id,
        title="Persistence Test",
        body="Checking persisted status",
    )
    db.commit()

    # Mark read
    client.post(
        f"/api/notifications/{notif.id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Simulate refresh via GET /api/notifications
    list_resp = client.get(
        "/api/notifications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.status_code == 200
    items = list_resp.json()
    item = next((i for i in items if i["id"] == notif.id), None)
    assert item is not None
    assert item["is_read"] is True
    assert item["unread"] is False
    assert item["read_at"] is not None

    db.query(Notification).filter(Notification.id == notif.id).delete()
    db.commit()

def test_4_ownership_isolation_cross_user_forbidden(db: Session, test_users):
    emp = test_users["emp"]
    other_emp = test_users["other_emp"]
    emp_token = create_token(emp)

    # Create notification belonging to other_emp
    notif = create_notification(
        db=db,
        recipient_id=other_emp.id,
        title="Private Notice",
        body="Only for other_emp",
    )
    db.commit()

    # emp attempts to mark other_emp's notification as read -> must return 403 Forbidden
    resp = client.post(
        f"/api/notifications/{notif.id}/read",
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    assert resp.status_code == 403

    db.query(Notification).filter(Notification.id == notif.id).delete()
    db.commit()

def test_5_manager_and_hr_mark_read_behavior(db: Session, test_users):
    mgr = test_users["mgr"]
    hr = test_users["hr"]
    mgr_token = create_token(mgr)
    hr_token = create_token(hr)

    # Manager notification
    mgr_notif = create_notification(
        db=db,
        recipient_id=mgr.id,
        title="Manager Alert",
        body="Pending team approval",
    )
    db.commit()

    r_mgr = client.post(
        f"/api/notifications/{mgr_notif.id}/read",
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert r_mgr.status_code == 200
    assert r_mgr.json()["is_read"] is True

    # HR notification
    hr_notif = create_notification(
        db=db,
        recipient_id=hr.id,
        title="HR Audit Notice",
        body="Weekly review ready",
    )
    db.commit()

    r_hr = client.post(
        f"/api/notifications/{hr_notif.id}/read",
        headers={"Authorization": f"Bearer {hr_token}"},
    )
    assert r_hr.status_code == 200
    assert r_hr.json()["is_read"] is True

    db.query(Notification).filter(Notification.id.in_([mgr_notif.id, hr_notif.id])).delete(synchronize_session=False)
    db.commit()
