from __future__ import annotations
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..models import PermissionRequest, User
from .audit_service import log_audit
from .notification_service import create_notification, notify_hr_role


def apply_permission(db: Session, user: User, data: dict) -> PermissionRequest:
    d_str = data.get("date")
    t_str = data.get("requested_checkout_time") or data.get("time") or "04:30 PM"
    reason = data.get("reason", "").strip()

    target_date = date.today()
    if d_str:
        try:
            target_date = datetime.strptime(d_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    req = PermissionRequest(
        employee_id=user.id,
        employee_name=user.name,
        department=user.department or "Engineering",
        role=user.role,
        date=target_date,
        requested_checkout_time=t_str,
        reason=reason,
        status="Pending",
        created_at=datetime.utcnow(),
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    log_audit(
        db,
        actor=user,
        action="PERMISSION_APPLIED",
        target_type="permission_request",
        target_id=req.id,
        new_value={"date": str(target_date), "requested_checkout_time": t_str, "reason": reason},
    )

    # Phase 4.C: Notify Manager
    if user.manager_id:
        create_notification(
            db,
            recipient_id=user.manager_id,
            title="New Permission Request Submitted",
            body=f"{user.name} requested early check-out at {t_str} for {target_date.strftime('%d %b')}.",
            notification_type="PERMISSION_REQUEST_SUBMITTED",
            entity_type="permission",
            entity_id=req.id,
            dedup_key=f"mgr_perm_req_{req.id}",
            link_url="/manager/permission-requests",
        )
    # Phase 5: Notify HR
    notify_hr_role(
        db,
        title="New Permission Request",
        body=f"{user.name} ({user.department}) requested early check-out at {t_str} for {target_date.strftime('%d %b')}.",
        notification_type="PERMISSION_REQUEST_SUBMITTED",
        entity_type="permission",
        entity_id=req.id,
        dedup_key_prefix=f"hr_perm_req_{req.id}",
        link_url="/hr/attendance",
    )

    return req


def get_my_permissions(db: Session, user: User) -> list[dict]:
    rows = (
        db.query(PermissionRequest)
        .filter(PermissionRequest.employee_id == user.id)
        .order_by(PermissionRequest.id.desc())
        .all()
    )
    return [
        {
            "id": f"PR-{r.id}",
            "raw_id": r.id,
            "date": r.date.strftime("%d %b %Y"),
            "requested_checkout_time": r.requested_checkout_time,
            "reason": r.reason,
            "status": r.status,
            "approver": r.approver_name or r.approved_by or "—",
            "applied_at": r.created_at.strftime("%d %b %Y, %I:%M %p") if r.created_at else "—",
        }
        for r in rows
    ]


def get_team_permissions(db: Session, manager_user: User) -> list[dict]:
    if manager_user.role == "hr":
        team_members = db.query(User).filter(User.role == "employee").all()
    else:
        team_members = (
            db.query(User)
            .filter(
                or_(
                    User.manager_name == manager_user.name,
                    User.manager_id == manager_user.id,
                )
            )
            .all()
        )
        if not team_members:
            team_members = db.query(User).filter(User.department == manager_user.department, User.role == "employee").all()
    member_ids = [m.id for m in team_members if m.id != manager_user.id]

    rows = (
        db.query(PermissionRequest)
        .filter(PermissionRequest.employee_id.in_(member_ids))
        .order_by(PermissionRequest.id.desc())
        .all()
    )
    return [
        {
            "id": f"PR-{r.id}",
            "raw_id": r.id,
            "employee": r.employee_name,
            "empId": r.employee_id,
            "department": r.department,
            "role": r.role,
            "date": r.date.strftime("%d %b %Y"),
            "requested_checkout_time": r.requested_checkout_time,
            "reason": r.reason,
            "status": r.status,
            "applied_at": r.created_at.strftime("%d %b %Y, %I:%M %p") if r.created_at else "—",
        }
        for r in rows
    ]


def get_all_permissions_hr(db: Session) -> list[dict]:
    rows = db.query(PermissionRequest).order_by(PermissionRequest.id.desc()).all()
    result = []
    for r in rows:
        u = db.query(User).filter(User.id == r.employee_id).first()
        emp_code = u.employee_code if u else f"E{r.employee_id}"
        emp_name = r.employee_name or (u.name if u else f"Employee #{r.employee_id}")
        result.append({
            "id": f"PR-{r.id}",
            "raw_id": r.id,
            "employee": emp_name,
            "employee_id": emp_code,
            "empId": emp_code,
            "department": r.department,
            "role": r.role,
            "date": r.date.strftime("%d %b %Y"),
            "requested_checkout_time": r.requested_checkout_time,
            "reason": r.reason,
            "status": r.status,
            "approver": r.approver_name or r.approved_by or "—",
            "approved_at": r.approved_at.strftime("%d %b %Y, %I:%M %p") if r.approved_at else "—",
        })
    return result


def update_permission_status(
    db: Session,
    perm_id: int,
    status: str,
    approver: User,
) -> PermissionRequest:
    req = db.query(PermissionRequest).filter(PermissionRequest.id == perm_id).first()
    if not req:
        raise ValueError("Permission request not found")

    if req.employee_id == approver.id:
        raise ValueError("Cannot approve own permission request.")

    old_status = req.status
    req.status = status
    req.approved_by = str(approver.id)
    req.approver_name = approver.name
    req.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(req)

    log_audit(
        db,
        actor=approver,
        action=f"PERMISSION_{status.upper()}",
        target_type="permission_request",
        target_id=req.id,
        old_value={"status": old_status},
        new_value={"status": status, "approver": approver.name},
    )

    # Phase 3.I: Notify Employee
    create_notification(
        db,
        recipient_id=req.employee_id,
        title=f"Permission Request {status}",
        body=f"Your permission request for {req.date.strftime('%d %b')} ({req.requested_checkout_time}) was {status.lower()} by {approver.name}.",
        notification_type=f"PERMISSION_{status.upper()}",
        entity_type="permission",
        entity_id=req.id,
        priority="high" if status == "Rejected" else "normal",
        link_url="/employee/attendance",
        dedup_key=f"perm_decided_{req.id}_{status}",
    )

    return req


def cancel_permission(db: Session, perm_id: int, user: User) -> PermissionRequest:
    req = db.query(PermissionRequest).filter(PermissionRequest.id == perm_id).first()
    if not req:
        raise ValueError("Permission request not found")

    if req.employee_id != user.id and user.role != "hr":
        raise ValueError("You can only cancel your own permission requests.")

    if req.status != "Pending":
        raise ValueError(f"Cannot cancel permission request that is already {req.status}.")

    req.status = "Cancelled"
    req.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(req)

    log_audit(
        db,
        actor=user,
        action="PERMISSION_CANCELLED",
        target_type="permission_request",
        target_id=req.id,
        old_value={"status": "Pending"},
        new_value={"status": "Cancelled"},
    )
    return req
