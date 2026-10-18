from __future__ import annotations
from datetime import datetime, date, timedelta
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

from ..models import Notification, User, Task


def format_relative_time(dt: datetime | None) -> str:
    if not dt:
        return "Now"
    now = datetime.utcnow()
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        mins = max(1, seconds // 60)
        return f"{mins}m ago"
    elif seconds < 86400:
        hours = max(1, seconds // 3600)
        return f"{hours}h ago"
    elif seconds < 172800:
        return "Yesterday"
    elif seconds < 604800:
        days = seconds // 86400
        return f"{days}d ago"
    else:
        return dt.strftime("%d %b")


def create_notification(
    db: Session,
    recipient_id: int,
    title: str,
    body: str,
    notification_type: str = "GENERAL",
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    priority: str = "normal",  # low, normal, high, critical
    link_url: str | None = None,
    dedup_key: str | None = None,
    group_key: str | None = None,
    expires_at: datetime | None = None,
    allow_grouping: bool = True,
) -> Notification | None:
    """Create a validated, deduplicated, and optionally grouped notification for a recipient."""
    if not recipient_id or not title or not body:
        return None

    # Verify recipient exists
    user = db.query(User).filter(User.id == recipient_id).first()
    if not user:
        return None

    # Default link_url based on role and entity if not explicitly provided
    if not link_url and entity_type:
        role = user.role or "employee"
        if entity_type == "task":
            link_url = "/employee/work" if role == "employee" else ("/manager/work-process" if role == "manager" else "/hr/tasks")
        elif entity_type in ("leave", "leave_request"):
            link_url = "/employee/leave" if role == "employee" else ("/manager/leave-requests" if role == "manager" else "/hr/leave")
        elif entity_type in ("permission", "permission_request"):
            link_url = "/employee/attendance" if role == "employee" else ("/manager/permission-requests" if role == "manager" else "/hr/attendance")
        elif entity_type in ("attendance", "attendance_correction"):
            link_url = "/employee/attendance" if role == "employee" else ("/manager/attendance" if role == "manager" else "/hr/attendance")
        elif entity_type == "unblock_request":
            link_url = "/employee/work" if role == "employee" else ("/manager/work-process" if role == "manager" else "/hr/tasks")
        elif entity_type == "burnout":
            link_url = "/employee/burnout" if role == "employee" else ("/manager/burnout" if role == "manager" else "/hr/risk-monitoring")
        elif entity_type == "intervention":
            link_url = "/employee/recommendations" if role == "employee" else "/hr/interventions"

    # Deduplication Check (Phase 9)
    if dedup_key:
        existing = (
            db.query(Notification)
            .filter(
                Notification.employee_id == recipient_id,
                Notification.dedup_key == dedup_key,
                Notification.is_archived == False,
            )
            .first()
        )
        if existing:
            # Already delivered this exact business event notification
            return existing

    # Repetitive Low-Priority Grouping (Phase 10)
    # Critical and high-priority notifications are NEVER grouped into a generic summary
    if allow_grouping and group_key and priority in ("low", "normal"):
        recent_window = datetime.utcnow() - timedelta(hours=24)
        grouped_existing = (
            db.query(Notification)
            .filter(
                Notification.employee_id == recipient_id,
                Notification.group_key == group_key,
                Notification.is_read == False,
                Notification.is_archived == False,
                Notification.created_at >= recent_window,
            )
            .order_by(Notification.id.desc())
            .first()
        )
        if grouped_existing:
            # Update existing grouped notification summary
            grouped_existing.title = title
            grouped_existing.body = f"{body} (Updated multiple times)"
            grouped_existing.time = "Now"
            grouped_existing.created_at = datetime.utcnow()
            grouped_existing.unread = 1
            grouped_existing.is_read = False
            return grouped_existing

    entity_id_str = str(entity_id) if entity_id is not None else None

    notif = Notification(
        employee_id=recipient_id,
        notification_type=notification_type,
        title=title,
        body=body,
        time="Now",
        unread=1,
        is_read=False,
        read_at=None,
        is_archived=False,
        archived_at=None,
        entity_type=entity_type,
        entity_id=entity_id_str,
        dedup_key=dedup_key,
        group_key=group_key,
        priority=priority,
        link_url=link_url,
        expires_at=expires_at,
        created_at=datetime.utcnow(),
    )
    db.add(notif)
    db.flush()
    return notif


def notify_hr_role(
    db: Session,
    title: str,
    body: str,
    notification_type: str = "HR_ACTION_REQUIRED",
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    priority: str = "normal",
    link_url: str = "/hr/tasks",
    dedup_key_prefix: str | None = None,
) -> list[Notification]:
    """Notify all authorized HR personnel with deduplication per HR user."""
    hr_users = db.query(User).filter(User.role == "hr").all()
    created = []
    for hr in hr_users:
        dedup_key = f"{dedup_key_prefix}_hr_{hr.id}" if dedup_key_prefix else None
        n = create_notification(
            db=db,
            recipient_id=hr.id,
            title=title,
            body=body,
            notification_type=notification_type,
            entity_type=entity_type,
            entity_id=entity_id,
            priority=priority,
            link_url=link_url,
            dedup_key=dedup_key,
        )
        if n:
            created.append(n)
    return created


def get_user_notifications(
    db: Session,
    user: User,
    limit: int = 50,
    include_archived: bool = False,
) -> list[dict[str, Any]]:
    """Retrieve active notifications for the authenticated user, enforcing the 7-day read retention policy."""
    # Enforce retention policy: read notifications older than 7 days stop cluttering the active list
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    (
        db.query(Notification)
        .filter(
            Notification.employee_id == user.id,
            Notification.is_read == True,
            Notification.is_archived == False,
            or_(Notification.read_at <= seven_days_ago, Notification.created_at <= seven_days_ago),
        )
        .update(
            {"is_archived": True, "archived_at": datetime.utcnow()},
            synchronize_session=False,
        )
    )
    db.commit()

    query = db.query(Notification).filter(Notification.employee_id == user.id)
    if not include_archived:
        query = query.filter(Notification.is_archived == False)

    rows = query.order_by(Notification.is_read.asc(), Notification.created_at.desc()).limit(limit).all()

    out = []
    for n in rows:
        is_unread = not bool(n.is_read) and bool(n.unread)
        out.append({
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "time": format_relative_time(n.created_at),
            "unread": is_unread,
            "is_read": bool(n.is_read),
            "read_at": n.read_at.strftime("%Y-%m-%d %H:%M:%S") if n.read_at else None,
            "is_archived": bool(n.is_archived),
            "notification_type": n.notification_type or "GENERAL",
            "entity_type": n.entity_type,
            "entity_id": n.entity_id,
            "priority": n.priority or "normal",
            "link_url": n.link_url,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M:%S") if n.created_at else None,
        })
    return out


def get_unread_count(db: Session, user: User) -> int:
    """Return fast count of unread, non-archived notifications for the authenticated user."""
    return (
        db.query(func.count(Notification.id))
        .filter(
            Notification.employee_id == user.id,
            Notification.is_read == False,
            Notification.is_archived == False,
        )
        .scalar()
        or 0
    )


def mark_notification_as_read(db: Session, notification_id: int, user: User) -> Notification:
    """Mark a single notification as read with strict recipient authorization check."""
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise ValueError("Notification not found")
    if notif.employee_id != user.id:
        raise PermissionError("Unauthorized: You cannot access or modify another user's notifications.")

    if not notif.is_read or not notif.read_at:
        notif.read_at = datetime.utcnow()
    notif.is_read = True
    notif.unread = 0
    db.commit()
    db.refresh(notif)
    return notif


def mark_all_as_read(db: Session, user: User) -> int:
    """Mark all active notifications for the authenticated user as read."""
    count = (
        db.query(Notification)
        .filter(
            Notification.employee_id == user.id,
            Notification.is_read == False,
            Notification.is_archived == False,
        )
        .update(
            {"is_read": True, "unread": 0, "read_at": datetime.utcnow()},
            synchronize_session=False,
        )
    )
    db.commit()
    return count


def archive_notification(db: Session, notification_id: int, user: User) -> Notification:
    """Archive a notification for the authenticated user."""
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise ValueError("Notification not found")
    if notif.employee_id != user.id:
        raise PermissionError("Unauthorized: You cannot access or modify another user's notifications.")

    notif.is_archived = True
    notif.archived_at = datetime.utcnow()
    db.commit()
    db.refresh(notif)
    return notif


def run_notification_retention_cleanup(db: Session) -> dict[str, int]:
    """Retention & Cleanup Policy (Phase 8):
    1. Read notifications: Auto-archive after 7 days from read_at or creation.
    2. Archived notifications: Permanently purge after 30 days from archived_at.
    3. Critical unread notifications (e.g. pending approvals, verification) are NEVER purged.
    4. Underlying task, attendance, leave, and audit records are completely independent and untouched.
    """
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    # 1. Auto-archive read notifications older than 7 days
    archived_count = (
        db.query(Notification)
        .filter(
            Notification.is_read == True,
            Notification.is_archived == False,
            or_(Notification.read_at <= seven_days_ago, Notification.created_at <= seven_days_ago),
        )
        .update(
            {"is_archived": True, "archived_at": now},
            synchronize_session=False,
        )
    )

    # 2. Safely purge eligible non-critical archived notifications older than 30 days
    # Critical and unresolved items are preserved
    purged_count = (
        db.query(Notification)
        .filter(
            Notification.is_archived == True,
            Notification.priority != "critical",
            or_(Notification.archived_at <= thirty_days_ago, Notification.created_at <= thirty_days_ago),
        )
        .delete(synchronize_session=False)
    )

    db.commit()
    return {"archived_count": archived_count, "purged_count": purged_count}


def check_and_generate_deadline_reminders(db: Session) -> int:
    """Idempotent scheduled check: Send a 24-hour deadline reminder to employees with upcoming tasks (Phase 3.B)."""
    today = date.today()
    tomorrow = today + timedelta(days=1)

    upcoming_tasks = (
        db.query(Task)
        .filter(
            Task.status.notin_(["Completed", "Blocked"]),
            (Task.completion_percentage < 100) | (Task.completion_percentage == None),
            or_(Task.due_date == tomorrow, Task.due_date == today),
        )
        .all()
    )

    sent = 0
    for t in upcoming_tasks:
        target_due = t.due_date or tomorrow
        dedup = f"deadline_reminder_24h_task_{t.id}_{target_due}"
        existing = (
            db.query(Notification)
            .filter(
                Notification.employee_id == t.employee_id,
                Notification.dedup_key == dedup,
            )
            .first()
        )
        if existing:
            continue

        due_str = t.deadline or str(target_due)
        n = create_notification(
            db=db,
            recipient_id=t.employee_id,
            title="Task Deadline Approaching",
            body=f"Task '{t.name}' is due soon ({due_str}). Please update your deliverables or submit progress.",
            notification_type="TASK_DEADLINE_REMINDER",
            entity_type="task",
            entity_id=t.id,
            priority="high",
            link_url="/employee/work",
            dedup_key=dedup,
        )
        if n is not None:
            sent += 1

    if sent > 0:
        db.commit()
    return sent
