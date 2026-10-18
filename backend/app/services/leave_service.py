from __future__ import annotations
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..models import LeaveRequest, User
from .audit_service import log_audit
from .notification_service import create_notification, notify_hr_role


def get_leave_balance(db: Session, user: User) -> list[dict]:
    # Calculate allocated vs taken
    current_year = date.today().year
    approved = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == user.id,
            LeaveRequest.status == "Approved",
        )
        .all()
    )

    taken = {"Casual Leave": 0.0, "Sick Leave": 0.0, "Earned Leave": 0.0, "Annual Leave": 0.0}
    for r in approved:
        dur = 0.5 if r.half_day_session in ("MORNING_HALF_DAY", "AFTERNOON_HALF_DAY") else 1.0
        if "day" in (r.duration or ""):
            try:
                dur = float(r.duration.split()[0])
            except Exception:
                pass
        t = r.leave_type or r.type or "Casual Leave"
        if t in taken:
            taken[t] += dur
        elif "Sick" in t:
            taken["Sick Leave"] += dur
        elif "Casual" in t:
            taken["Casual Leave"] += dur
        else:
            taken["Earned Leave"] += dur

    return [
        {"type": "Casual Leave", "remaining": max(0, int(12 - taken["Casual Leave"])), "total": 12},
        {"type": "Sick Leave", "remaining": max(0, int(8 - taken["Sick Leave"])), "total": 8},
        {"type": "Earned Leave", "remaining": max(0, int(15 - taken["Earned Leave"])), "total": 15},
    ]


def apply_leave(db: Session, user: User, data: dict) -> LeaveRequest:
    l_type = data.get("leave_type") or data.get("type") or "Casual Leave"
    start_str = data.get("start") or data.get("start_date")
    end_str = data.get("end") or data.get("end_date")
    half_day = data.get("half_day_session") or "FULL_DAY"
    reason = data.get("reason", "").strip()

    date_label = data.get("date") or (f"{start_str} – {end_str}" if start_str and end_str else (start_str or str(date.today())))

    start_d = None
    end_d = None
    if start_str:
        try:
            start_d = datetime.strptime(start_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if end_str:
        try:
            end_d = datetime.strptime(end_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if not start_d:
        start_d = date.today()
    if not end_d:
        end_d = start_d

    # Calculate duration
    if half_day in ("MORNING_HALF_DAY", "AFTERNOON_HALF_DAY"):
        duration = "0.5 day"
    else:
        num_days = max(1, (end_d - start_d).days + 1)
        duration = f"{num_days} day{'s' if num_days > 1 else ''}"

    req = LeaveRequest(
        employee_id=user.id,
        employee_name=user.name,
        department=user.department or "Engineering",
        role=user.role,
        type=l_type,
        leave_type=l_type,
        date=date_label,
        start_date=start_d,
        end_date=end_d,
        duration=duration,
        half_day_session=half_day,
        reason=reason,
        status="Pending",
        manager_status="Pending",
        created_at=datetime.utcnow(),
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    log_audit(
        db,
        actor=user,
        action="LEAVE_APPLIED",
        target_type="leave_request",
        target_id=req.id,
        new_value={"type": l_type, "duration": duration, "reason": reason},
    )

    # Phase 4.C: Notify Manager
    if user.manager_id:
        create_notification(
            db,
            recipient_id=user.manager_id,
            title="New Leave Request Submitted",
            body=f"{user.name} applied for {l_type} ({date_label}).",
            notification_type="LEAVE_REQUEST_SUBMITTED",
            entity_type="leave",
            entity_id=req.id,
            dedup_key=f"mgr_leave_req_{req.id}",
            link_url="/manager/leave-requests",
        )
    # Phase 5: Notify HR
    notify_hr_role(
        db,
        title="New Leave Request",
        body=f"{user.name} ({user.department}) applied for {l_type} ({date_label}).",
        notification_type="LEAVE_REQUEST_SUBMITTED",
        entity_type="leave",
        entity_id=req.id,
        dedup_key_prefix=f"hr_leave_req_{req.id}",
        link_url="/hr/leave",
    )

    return req


def get_my_leaves(db: Session, user: User) -> dict:
    hist = (
        db.query(LeaveRequest)
        .filter(LeaveRequest.employee_id == user.id)
        .order_by(LeaveRequest.id.desc())
        .all()
    )
    history = [
        {
            "id": f"L-{r.id}",
            "raw_id": r.id,
            "date": r.date or (r.start_date.strftime("%d %b %Y") if r.start_date else "—"),
            "type": r.leave_type or r.type,
            "duration": r.duration,
            "reason": r.reason,
            "status": r.status,
            "half_day_session": r.half_day_session,
            "applied_at": r.created_at.strftime("%d %b %Y, %I:%M %p") if r.created_at else "—",
            "approved_by": r.approver_name or r.approved_by or "—",
        }
        for r in hist
    ]
    return {
        "balance": get_leave_balance(db, user),
        "history": history,
    }


def get_team_leaves(db: Session, manager_user: User) -> list[dict]:
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
        db.query(LeaveRequest)
        .filter(LeaveRequest.employee_id.in_(member_ids))
        .order_by(LeaveRequest.id.desc())
        .all()
    )
    return [
        {
            "id": f"LR-{r.id}",
            "raw_id": r.id,
            "employee": r.employee_name,
            "empId": r.employee_id,
            "department": r.department,
            "role": r.role,
            "type": r.leave_type or r.type,
            "date": r.date,
            "duration": r.duration,
            "reason": r.reason,
            "status": r.status,
            "half_day_session": r.half_day_session,
            "applied_at": r.created_at.strftime("%d %b %Y, %I:%M %p") if r.created_at else "—",
        }
        for r in rows
    ]


def get_all_leaves_hr(
    db: Session,
    employee: str | None = None,
    department: str | None = None,
    role: str | None = None,
    leave_type: str | None = None,
    status: str | None = None,
) -> list[dict]:
    query = db.query(LeaveRequest).order_by(LeaveRequest.id.desc())
    if department and department != "All":
        query = query.filter(LeaveRequest.department == department)
    if role and role != "All":
        query = query.filter(LeaveRequest.role == role)
    if leave_type and leave_type != "All":
        query = query.filter(or_(LeaveRequest.leave_type == leave_type, LeaveRequest.type == leave_type))
    if status and status != "All":
        query = query.filter(LeaveRequest.status == status)

    rows = query.all()
    all_users = db.query(User).all()
    user_map = {u.id: u for u in all_users}
    result = []
    for r in rows:
        u = user_map.get(r.employee_id)
        emp_code = u.employee_code if u else f"E{r.employee_id}"
        emp_name = r.employee_name or (u.name if u else f"Employee #{r.employee_id}")

        if employee and employee.lower() not in emp_name.lower() and employee.lower() not in emp_code.lower():
            continue

        result.append({
            "id": f"LR-{r.id}",
            "raw_id": r.id,
            "employee": emp_name,
            "employee_id": emp_code,
            "empId": emp_code,
            "department": r.department or (u.department if u else "Engineering"),
            "role": r.role or (u.role if u else "employee"),
            "leave_type": r.leave_type or r.type,
            "type": r.leave_type or r.type,
            "from_date": r.start_date.strftime("%d %b %Y") if r.start_date else r.date,
            "to_date": r.end_date.strftime("%d %b %Y") if r.end_date else r.date,
            "date": r.date,
            "duration": r.duration,
            "reason": r.reason,
            "applied_date": r.created_at.strftime("%d %b %Y") if r.created_at else "—",
            "manager_approval": r.manager_status or "Approved",
            "status": r.status,
            "final_status": r.status,
            "approver": r.approver_name or r.approved_by or "—",
            "approval_timestamp": r.approved_at.strftime("%d %b %Y, %I:%M %p") if r.approved_at else "—",
        })
    return result


def update_leave_status(
    db: Session,
    leave_id: int,
    status: str,
    approver: User,
) -> LeaveRequest:
    req = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not req:
        raise ValueError("Leave request not found")

    # Manager cannot approve their own leave
    if req.employee_id == approver.id:
        raise ValueError("Managers cannot approve their own leave requests.")

    old_status = req.status
    req.status = status
    req.manager_status = status
    req.approved_by = str(approver.id)
    req.approver_name = approver.name
    req.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(req)

    log_audit(
        db,
        actor=approver,
        action=f"LEAVE_{status.upper()}",
        target_type="leave_request",
        target_id=req.id,
        old_value={"status": old_status},
        new_value={"status": status, "approver": approver.name},
    )

    # Phase 3.I: Notify Employee
    create_notification(
        db,
        recipient_id=req.employee_id,
        title=f"Leave Request {status}",
        body=f"Your {req.leave_type or 'leave'} request for {req.date} has been {status.lower()} by {approver.name}.",
        notification_type=f"LEAVE_{status.upper()}",
        entity_type="leave",
        entity_id=req.id,
        priority="high" if status == "Rejected" else "normal",
        link_url="/employee/leave",
        dedup_key=f"leave_decided_{req.id}_{status}",
    )

    # Refresh prediction for leave applicant
    applicant = db.query(User).filter(User.id == req.employee_id).first()
    if applicant:
        try:
            from .burnout_service import predict_for_employee
            predict_for_employee(db, applicant, persist=True)
        except Exception:
            pass

    return req


def cancel_leave(db: Session, leave_id: int, user: User) -> LeaveRequest:
    req = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not req:
        raise ValueError("Leave request not found")

    if req.employee_id != user.id and user.role != "hr":
        raise ValueError("You can only cancel your own leave requests.")

    if req.status != "Pending":
        raise ValueError(f"Cannot cancel leave request that is already {req.status}.")

    req.status = "Cancelled"
    req.manager_status = "Cancelled"
    req.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(req)

    log_audit(
        db,
        actor=user,
        action="LEAVE_CANCELLED",
        target_type="leave_request",
        target_id=req.id,
        old_value={"status": "Pending"},
        new_value={"status": "Cancelled"},
    )
    return req
