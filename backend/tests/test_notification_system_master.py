import pytest
from datetime import datetime, date, timedelta
from app.database import SessionLocal
from app.models import User, Task, LeaveRequest, Notification, TaskUnblockRequest, Attendance, Prediction
from app.services.notification_service import (
    create_notification,
    notify_hr_role,
    get_user_notifications,
    get_unread_count,
    mark_notification_as_read,
    mark_all_as_read,
    archive_notification,
    run_notification_retention_cleanup,
    check_and_generate_deadline_reminders,
)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_users(db):
    emp = db.query(User).filter(User.role == "employee").first()
    mgr = db.query(User).filter(User.role == "manager").first()
    hr = db.query(User).filter(User.role == "hr").first()
    assert emp and mgr and hr
    return {"employee": emp, "manager": mgr, "hr": hr}


def test_notification_creation_and_deduplication(db, test_users):
    emp = test_users["employee"]
    dedup = f"test_task_assign_unit_{emp.id}_{datetime.utcnow().timestamp()}"

    # 1. Create notification
    n1 = create_notification(
        db,
        recipient_id=emp.id,
        title="Unit Test Task",
        body="You have a new unit test task assigned.",
        notification_type="TASK_ASSIGNED",
        entity_type="task",
        entity_id=999,
        priority="normal",
        link_url="/employee/work",
        dedup_key=dedup,
    )
    db.commit()
    assert n1 is not None
    assert n1.employee_id == emp.id
    assert n1.unread == 1
    assert n1.is_read == False

    # 2. Duplicate prevention (Phase 9)
    n2 = create_notification(
        db,
        recipient_id=emp.id,
        title="Unit Test Task Duplicate",
        body="Duplicate attempt.",
        notification_type="TASK_ASSIGNED",
        entity_type="task",
        entity_id=999,
        priority="normal",
        link_url="/employee/work",
        dedup_key=dedup,
    )
    db.commit()
    # Must return the existing notification without creating a second record
    assert n2.id == n1.id

    # Cleanup
    db.delete(n1)
    db.commit()


def test_read_unread_and_ownership_security(db, test_users):
    emp = test_users["employee"]
    mgr = test_users["manager"]

    # Create notification for employee
    n = create_notification(
        db,
        recipient_id=emp.id,
        title="Security Test Notice",
        body="Private notification for employee.",
        notification_type="GENERAL",
    )
    db.commit()

    try:
        # Verify initial unread count
        initial_unread = get_unread_count(db, emp)
        assert initial_unread >= 1

        # Security check (Phase 14): Manager cannot read or modify employee's notification
        with pytest.raises(PermissionError):
            mark_notification_as_read(db, n.id, mgr)

        # Employee reads their own notification
        read_n = mark_notification_as_read(db, n.id, emp)
        assert read_n.is_read == True
        assert read_n.unread == 0
        assert read_n.read_at is not None

        # Verify unread count decremented
        after_unread = get_unread_count(db, emp)
        assert after_unread == initial_unread - 1

    finally:
        db.delete(n)
        db.commit()


def test_mark_all_as_read_isolation(db, test_users):
    emp = test_users["employee"]
    mgr = test_users["manager"]

    # Create 2 for emp, 1 for mgr
    n1 = create_notification(db, emp.id, "Emp Notice 1", "Body 1")
    n2 = create_notification(db, emp.id, "Emp Notice 2", "Body 2")
    n_mgr = create_notification(db, mgr.id, "Mgr Notice", "Mgr Body")
    db.commit()

    try:
        # Emp marks all read
        marked = mark_all_as_read(db, emp)
        assert marked >= 2

        # Verify emp notifications are read
        db.refresh(n1)
        db.refresh(n2)
        assert n1.is_read == True
        assert n2.is_read == True

        # Verify mgr notification remains UNREAD (strict isolation!)
        db.refresh(n_mgr)
        assert n_mgr.is_read == False
        assert n_mgr.unread == 1

    finally:
        db.delete(n1)
        db.delete(n2)
        db.delete(n_mgr)
        db.commit()


def test_repetitive_notification_grouping(db, test_users):
    emp = test_users["employee"]
    grp = f"task_progress_group_{emp.id}_task_77"

    # 1. First low-priority progress update
    n1 = create_notification(
        db,
        recipient_id=emp.id,
        title="Task Progress Updated",
        body="Progress changed to 20%",
        notification_type="TASK_PROGRESS",
        priority="normal",
        group_key=grp,
        allow_grouping=True,
    )
    db.commit()

    # 2. Second minor progress update within grouping window
    n2 = create_notification(
        db,
        recipient_id=emp.id,
        title="Task Progress Updated",
        body="Progress changed to 35%",
        notification_type="TASK_PROGRESS",
        priority="normal",
        group_key=grp,
        allow_grouping=True,
    )
    db.commit()

    try:
        # Grouping should update the existing item rather than spamming
        assert n2.id == n1.id
        assert "Updated multiple times" in n2.body
    finally:
        db.delete(n1)
        db.commit()


def test_retention_and_cleanup_policy(db, test_users):
    emp = test_users["employee"]

    # 1. Create a read notification simulating read 8 days ago
    old_read_notif = create_notification(
        db,
        recipient_id=emp.id,
        title="Old Read Notice",
        body="Notice read long ago",
        notification_type="GENERAL",
    )
    old_read_notif.is_read = True
    old_read_notif.unread = 0
    old_read_notif.read_at = datetime.utcnow() - timedelta(days=8)
    old_read_notif.created_at = datetime.utcnow() - timedelta(days=9)

    # 2. Create an archived notification older than 31 days
    old_archived_notif = create_notification(
        db,
        recipient_id=emp.id,
        title="Expired Archived Notice",
        body="Very old notification",
        notification_type="GENERAL",
    )
    old_archived_notif.is_archived = True
    old_archived_notif.archived_at = datetime.utcnow() - timedelta(days=32)
    old_archived_notif.created_at = datetime.utcnow() - timedelta(days=40)

    # 3. Create a critical unread notification older than 30 days (MUST NEVER BE PURGED!)
    critical_unread_notif = create_notification(
        db,
        recipient_id=emp.id,
        title="Critical Security / Approval Alert",
        body="Critical alert requiring resolution",
        notification_type="SECURITY_ALERT",
        priority="critical",
    )
    critical_unread_notif.created_at = datetime.utcnow() - timedelta(days=35)

    db.commit()
    old_read_id = old_read_notif.id
    old_archived_id = old_archived_notif.id
    critical_id = critical_unread_notif.id

    try:
        # Run retention cleanup
        res = run_notification_retention_cleanup(db)
        assert res["archived_count"] >= 1

        # Check old read notif is now archived
        read_check = db.query(Notification).filter(Notification.id == old_read_id).first()
        assert read_check is not None
        assert read_check.is_archived == True

        # Check old archived notif was purged
        purged_check = db.query(Notification).filter(Notification.id == old_archived_id).first()
        assert purged_check is None

        # Check critical unread notif was preserved
        crit_check = db.query(Notification).filter(Notification.id == critical_id).first()
        assert crit_check is not None
        assert crit_check.is_read == False

    finally:
        db.query(Notification).filter(Notification.id.in_([old_read_id, critical_id])).delete(synchronize_session=False)
        db.commit()


def test_deadline_reminder_generation(db, test_users):
    emp = test_users["employee"]
    tomorrow = date.today() + timedelta(days=1)

    # Create a test task due tomorrow
    t = Task(
        employee_id=emp.id,
        name="Unit Test Approaching Task",
        deadline=tomorrow.strftime("%d %b %Y"),
        due_date=tomorrow,
        status="In Progress",
        completion_percentage=40,
        difficulty=3,
        created_at=datetime.utcnow(),
    )
    db.add(t)
    db.commit()
    db.refresh(t)

    try:
        # Run deadline check
        reminders_sent = check_and_generate_deadline_reminders(db)
        assert reminders_sent >= 1

        # Check that reminder was created for employee
        notifs = get_user_notifications(db, emp)
        reminder = next((n for n in notifs if n["entity_id"] == str(t.id) and "Approaching" in n["title"]), None)
        assert reminder is not None
        assert reminder["priority"] == "high"
        assert reminder["link_url"] == "/employee/work"

        # Idempotent re-run should NOT create duplicate reminder (dedup check!)
        second_run_sent = check_and_generate_deadline_reminders(db)
        # Verify employee still has only 1 reminder for this task
        reminders_for_task = [n for n in get_user_notifications(db, emp) if n["entity_id"] == str(t.id)]
        assert len(reminders_for_task) == 1

    finally:
        # Clean up test task and its notification
        db.query(Notification).filter(Notification.entity_id == str(t.id)).delete(synchronize_session=False)
        db.delete(t)
        db.commit()
