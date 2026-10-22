from __future__ import annotations
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..models import Task, User, Communication, TaskUnblockRequest, Notification, Attendance, Survey
from .audit_service import log_audit
from .semantic_service import analyze_communication


def derive_task_status_from_progress(progress: int) -> str:
    """Authoritative backend function for automatic task status determination:
    0% -> Not Started
    1%–75% -> In Progress
    76%–99% -> Almost Completed
    100% -> Completed
    """
    try:
        p = int(progress)
    except (TypeError, ValueError):
        raise ValueError("Progress must be an integer between 0 and 100")
    if p < 0 or p > 100:
        raise ValueError("Progress must be an integer between 0 and 100")

    if p <= 0:
        return "Not Started"
    elif p <= 75:
        return "In Progress"
    elif p <= 99:
        return "Almost Completed"
    else:
        return "Completed"


def _parse_deadline_to_date(deadline_str: str | None) -> date | None:
    if not deadline_str:
        return None
    s = str(deadline_str).strip()
    for fmt in ("%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%d %b", "%d %B"):
        try:
            d = datetime.strptime(s, fmt).date()
            if fmt in ("%d %b", "%d %B"):
                d = d.replace(year=date.today().year)
            return d
        except ValueError:
            pass
    return None


def check_and_block_overdue_tasks(db: Session, user_id: int | None = None) -> int:
    """Idempotent scheduled/on-demand check:
    If a task's deadline has passed and the task is not Completed, mark it Blocked.
    Preserves task progress, records blocking reason and timestamp.
    """
    today = date.today()
    query = db.query(Task).filter(Task.status.notin_(["Completed", "Blocked"]))
    if user_id is not None:
        query = query.filter(Task.employee_id == user_id)
    candidates = query.all()

    count = 0
    for t in candidates:
        is_overdue = False
        target_date = t.due_date or _parse_deadline_to_date(t.deadline)
        if target_date and target_date < today:
            is_overdue = True
        elif t.deadline and str(t.deadline).strip().lower() in ("yesterday", "overdue"):
            is_overdue = True

        if is_overdue:
            old_status = t.status
            t.status = "Blocked"
            t.missed_deadline_at = datetime.utcnow()
            if not t.blocked_reason:
                t.blocked_reason = f"Deadline missed on {target_date or t.deadline}"

            log_audit(
                db,
                actor=None,
                action="TASK_DEADLINE_BLOCKED",
                target_type="task",
                target_id=t.id,
                old_value={"status": old_status, "deadline": t.deadline},
                new_value={"status": "Blocked", "missed_deadline_at": str(t.missed_deadline_at)},
            )
            count += 1

            # Phase 3.C: Notify employee
            _notify_user(
                db,
                t.employee_id,
                "Task Blocked",
                f"Task '{t.name}' was marked Blocked due to deadline. You can submit an Unblock Request to HR.",
                notification_type="TASK_BLOCKED",
                entity_id=t.id,
                dedup_key=f"task_blocked_{t.id}_{today}",
                priority="high",
                link_url="/employee/work",
            )
            # Phase 4.C: Notify responsible manager
            assignee_u = db.query(User).filter(User.id == t.employee_id).first()
            if assignee_u and assignee_u.manager_id:
                _notify_user(
                    db,
                    assignee_u.manager_id,
                    "Team Task Blocked",
                    f"{assignee_u.name}'s task '{t.name}' is blocked due to deadline.",
                    notification_type="TEAM_TASK_BLOCKED",
                    entity_id=t.id,
                    dedup_key=f"mgr_blocked_{assignee_u.manager_id}_{t.id}_{today}",
                    priority="high",
                    link_url="/manager/work-process",
                )

    if count > 0:
        db.commit()
    return count


from .notification_service import (
    create_notification, notify_hr_role, check_and_generate_deadline_reminders
)


def _notify_hr_users(
    db: Session,
    title: str,
    body: str,
    entity_type: str = "task",
    entity_id: str | int | None = None,
    dedup_key_prefix: str | None = None,
    link_url: str = "/hr/tasks",
):
    notify_hr_role(
        db,
        title=title,
        body=body,
        notification_type="HR_ACTION_REQUIRED",
        entity_type=entity_type,
        entity_id=entity_id,
        link_url=link_url,
        dedup_key_prefix=dedup_key_prefix,
    )


def _notify_user(
    db: Session,
    user_id: int,
    title: str,
    body: str,
    notification_type: str = "TASK_NOTIFICATION",
    entity_type: str = "task",
    entity_id: str | int | None = None,
    dedup_key: str | None = None,
    group_key: str | None = None,
    link_url: str | None = None,
    priority: str = "normal",
):
    create_notification(
        db,
        recipient_id=user_id,
        title=title,
        body=body,
        notification_type=notification_type,
        entity_type=entity_type,
        entity_id=entity_id,
        dedup_key=dedup_key,
        group_key=group_key,
        link_url=link_url,
        priority=priority,
    )


def get_user_tasks(db: Session, user: User) -> dict:
    check_and_block_overdue_tasks(db, user.id)
    check_and_generate_deadline_reminders(db)

    tasks = db.query(Task).filter(Task.employee_id == user.id).order_by(Task.id.desc()).all()

    # Pre-fetch any active unblock requests for user's tasks
    task_ids = [t.id for t in tasks]
    unblock_reqs = {}
    if task_ids:
        active_reqs = (
            db.query(TaskUnblockRequest)
            .filter(TaskUnblockRequest.task_id.in_(task_ids))
            .order_by(TaskUnblockRequest.id.desc())
            .all()
        )
        for r in active_reqs:
            if r.task_id not in unblock_reqs:
                unblock_reqs[r.task_id] = {
                    "id": r.id,
                    "status": r.status,
                    "requested_new_deadline": r.requested_new_deadline,
                    "extension_reason": r.extension_reason,
                    "work_completed": r.work_completed,
                    "remaining_work": r.remaining_work,
                    "clarification_requested": r.clarification_requested,
                    "clarification_response": r.clarification_response,
                    "decision_reason": r.decision_reason,
                    "created_at": r.created_at.strftime("%d %b %Y, %I:%M %p") if r.created_at else "",
                }

    rows = []
    for t in tasks:
        is_completed = t.status == "Completed" or (t.completion_percentage or 0) >= 100
        is_blocked = t.status == "Blocked"
        active_req = unblock_reqs.get(t.id)

        rows.append({
            "id": f"T-{t.id}",
            "raw_id": t.id,
            "name": t.name,
            "title": t.name,
            "description": t.description or "",
            "priority": t.priority,
            "deadline": t.deadline or "Upcoming",
            "due_date": str(t.due_date) if t.due_date else None,
            "status": t.status,
            "difficulty": t.difficulty,
            "completion_percentage": t.completion_percentage or 0,
            "progress": t.completion_percentage or 0,
            "work_update": t.work_update or "",
            "blocked_reason": t.blocked_reason or "",
            "assigned_by": t.assigned_by_name or user.manager_name or "Manager",
            "assigned_by_id": t.assigned_by_id,
            "created_at": t.created_at.strftime("%d %b %Y") if t.created_at else "",
            "updated_at": t.updated_at.strftime("%d %b %Y, %I:%M %p") if t.updated_at else "",
            "completed_at": t.completed_at.strftime("%d %b %Y, %I:%M %p") if t.completed_at else "",
            "completed_by_id": t.completed_by_id,
            "verification_status": t.verification_status or "None",
            "verified_by_id": t.verified_by_id,
            "verified_at": t.verified_at.strftime("%d %b %Y, %I:%M %p") if t.verified_at else "",
            "verification_notes": t.verification_notes or "",
            "is_locked": is_completed,
            "is_blocked": is_blocked,
            "can_update": not is_completed and not is_blocked,
            "active_unblock_request": active_req,
        })

    completed = sum(1 for t in tasks if t.status in ("Completed", "Done"))
    almost_completed = sum(1 for t in tasks if t.status == "Almost Completed")
    in_progress = sum(1 for t in tasks if t.status == "In Progress")
    not_started = sum(1 for t in tasks if t.status in ("Not Started", "Pending"))
    blocked = sum(1 for t in tasks if t.status == "Blocked" or (t.blocked_reason and t.status not in ("Completed", "Done")))
    overdue = sum(1 for t in tasks if t.status == "Overdue")
    pending = not_started + in_progress + almost_completed
    n = max(len(tasks), 1)

    high_pri = sum(1 for t in tasks if t.priority in ("High", "Urgent"))

    today_d = date.today()
    monday = today_d - timedelta(days=today_d.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(5)]
    week_atts = {
        a.date: a
        for a in db.query(Attendance)
        .filter(Attendance.employee_id == user.id, Attendance.date.in_(week_dates))
        .all()
    }
    hours_week = []
    days_names = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    for i, wd in enumerate(week_dates):
        rec = week_atts.get(wd)
        h = round(rec.working_minutes / 60.0, 1) if (rec and rec.working_minutes) else 0.0
        ot = round(rec.overtime_minutes / 60.0, 1) if (rec and rec.overtime_minutes) else 0.0
        hours_week.append({"d": days_names[i], "day": days_names[i], "v": h, "hours": h, "ot": ot})

    return {
        "plan": {
            "tasksAssigned": len(tasks),
            "highPriority": high_pri,
            "deadlineToday": sum(1 for t in tasks if "today" in (t.deadline or "").lower()),
            "estimatedHours": max(6, len(tasks) * 2),
        },
        "summary": {
            "assigned": len(tasks),
            "completed": completed,
            "almost_completed": almost_completed,
            "in_progress": in_progress,
            "not_started": not_started,
            "pending": pending,
            "blocked": blocked,
            "overdue": overdue,
            "completion": round(100 * completed / n),
        },
        "tasks": rows,
        "hoursWeek": hours_week,
        "weekly_hours": hours_week,
    }


def create_task(db: Session, user: User, data: dict) -> Task:
    # Phase 2: Role-based task assignment enforcement
    if user.role == "employee":
        raise ValueError("Unauthorized: Employees cannot create tasks.")

    name = data.get("name") or data.get("title") or "Untitled Task"
    target_id = None

    raw_target = data.get("employee_id") or data.get("assigned_to")
    if raw_target is not None:
        if isinstance(raw_target, str) and (raw_target.startswith("E") or raw_target.startswith("M") or raw_target.startswith("H")):
            target_user = db.query(User).filter(User.employee_code == raw_target).first()
            if target_user:
                target_id = target_user.id
        else:
            try:
                target_id = int(str(raw_target).removeprefix("E").removeprefix("M").removeprefix("H"))
            except ValueError:
                pass

    if not target_id:
        if user.role == "hr":
            raise ValueError("HR must specify an employee or manager to assign the task to.")
        elif user.role == "manager":
            raise ValueError("Manager must specify a team member to assign the task to.")
        else:
            target_id = user.id

    target_u = db.query(User).filter(User.id == target_id).first()
    if not target_u:
        raise ValueError("Assigned target user not found.")

    if user.role == "manager":
        # Managers can only assign to their authorized team members
        if target_u.id == user.id:
            raise ValueError("Managers cannot create tasks for themselves.")
        if target_u.role == "hr":
            raise ValueError("Managers cannot assign tasks to HR.")
        is_team_member = (
            target_u.manager_id == user.id
            or target_u.manager_name == user.name
            or (target_u.department == user.department and target_u.role == "employee")
        )
        if not is_team_member:
            raise ValueError("Unauthorized: Managers can only assign tasks to their authorized team members.")

    pct = int(data.get("progress") if data.get("progress") is not None else (data.get("completion_percentage") or 0))
    status = derive_task_status_from_progress(pct)

    due_d = None
    deadline_str = data.get("deadline", "Upcoming")
    if deadline_str:
        due_d = _parse_deadline_to_date(deadline_str)

    task = Task(
        employee_id=target_id,
        assigned_by_id=user.id,
        assigned_by_name=user.name,
        name=name,
        description=data.get("description", ""),
        priority=data.get("priority", "Medium"),
        deadline=deadline_str,
        due_date=due_d,
        status=status,
        difficulty=int(data.get("difficulty", 3)),
        completion_percentage=pct,
        work_update=data.get("work_update"),
        blocked_reason=data.get("blocked_reason"),
        verification_status="None",
        created_at=datetime.utcnow(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    log_audit(
        db,
        actor=user,
        action="TASK_CREATED",
        target_type="task",
        target_id=task.id,
        new_value={"name": name, "assigned_to": target_id, "priority": task.priority, "status": status},
    )

    # Notify assignee
    _notify_user(
        db,
        target_id,
        "New Task Assigned",
        f"{user.name} assigned you a new task: '{name}'. Due: {task.deadline or 'Upcoming'}.",
        notification_type="TASK_ASSIGNED",
        entity_id=task.id,
        dedup_key=f"task_assigned_{task.id}_{target_id}",
        priority="high" if task.priority in ("High", "Urgent") else "normal",
        link_url="/employee/work" if target_u.role == "employee" else "/manager/work-process",
    )

    # Recalculate burnout prediction for assignee using central service (Part 2.2.B)
    try:
        from .burnout_service import recalculate_employee_burnout
        recalculate_employee_burnout(db, target_u.id, trigger_source="task_created", actor=user, persist=True)
    except Exception:
        pass

    return task


def update_task_details(db: Session, task_id: int, data: dict, user: User) -> tuple[Task, dict | None]:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError("Task not found")

    # Role validation
    if user.role == "employee" and task.employee_id != user.id:
        raise ValueError("Unauthorized: You can only update your own tasks.")
    if user.role == "manager":
        assignee_u = db.query(User).filter(User.id == task.employee_id).first()
        if assignee_u and assignee_u.id != user.id and assignee_u.manager_id != user.id and assignee_u.manager_name != user.name:
            if task.assigned_by_id != user.id:
                raise ValueError("Unauthorized: You can only update tasks for your team or assigned to you.")

    # Phase 4 Completed Lock: Locked against ordinary progress changes unless HR requested changes
    if (task.status == "Completed" or (task.completion_percentage or 0) >= 100) and task.verification_status != "Changes Requested":
        raise ValueError("Completed tasks are locked and cannot be modified. Awaiting HR verification.")

    # Phase 5 Blocked Lock: Locked until HR unblocks
    if task.status == "Blocked":
        raise ValueError("This task is Blocked due to deadline or dependency. Progress updates are locked. Please submit an Unblock Request to HR.")

    old_status = task.status
    old_progress = task.completion_percentage

    if "name" in data and data["name"] and str(data["name"]).strip():
        if user.role in ("manager", "hr"):
            task.name = str(data["name"]).strip()
    if "description" in data:
        task.description = data["description"]
    if "priority" in data and data["priority"]:
        if user.role in ("manager", "hr"):
            task.priority = data["priority"]
    if "deadline" in data and data["deadline"]:
        if user.role in ("manager", "hr"):
            task.deadline = data["deadline"]
            task.due_date = _parse_deadline_to_date(data["deadline"])
    if "difficulty" in data:
        try:
            task.difficulty = int(data["difficulty"])
        except Exception:
            pass

    # Phase 3 Automatic Task Status determination & status business rule validation
    explicit_status = data.get("status")
    progress_val = data.get("progress") if data.get("progress") is not None else data.get("completion_percentage")

    if "blocked_reason" in data and data["blocked_reason"] is not None:
        task.blocked_reason = str(data["blocked_reason"]).strip()

    if explicit_status:
        explicit_status_str = str(explicit_status).strip()
        if explicit_status_str.lower() == "blocked":
            reason = str(data.get("blocked_reason") if data.get("blocked_reason") is not None else (task.blocked_reason or "")).strip()
            if not reason:
                raise ValueError("A blocked reason is required when setting task status to Blocked.")
            task.status = "Blocked"
            task.blocked_reason = reason
        elif explicit_status_str.lower() == "completed":
            if progress_val is not None:
                try:
                    p = int(progress_val)
                    if p < 100:
                        raise ValueError("Completed status requires 100% progress.")
                except ValueError as ve:
                    if "Completed status" in str(ve):
                        raise
                    raise ValueError("Progress must be an integer between 0 and 100.")
            progress_val = 100

    if progress_val is not None:
        try:
            p = int(progress_val)
        except (TypeError, ValueError):
            raise ValueError("Progress must be an integer between 0 and 100.")
        if p < 0 or p > 100:
            raise ValueError("Progress must be an integer between 0 and 100.")

        task.completion_percentage = p
        if not (explicit_status and str(explicit_status).strip().lower() == "blocked"):
            derived_status = derive_task_status_from_progress(p)
            task.status = derived_status

        # Phase 4 Completed Task Lock & HR Verification queue submission
        if p == 100:
            was_resubmission = (task.verification_status == "Changes Requested")
            task.status = "Completed"
            task.completed_at = datetime.utcnow()
            task.completed_by_id = user.id
            task.verification_status = "Awaiting Verification"
            if was_resubmission:
                _notify_hr_users(
                    db,
                    title="Corrected Task Resubmitted for Verification",
                    body=f"{user.name} submitted corrected work for task '{task.name}' (100%). Ready for HR re-verification in the queue.",
                    entity_id=task.id,
                    dedup_key_prefix=f"task_resubmitted_{task.id}_{datetime.utcnow().date()}",
                )
            else:
                _notify_hr_users(
                    db,
                    title="Task Awaiting Verification",
                    body=f"{user.name} completed task '{task.name}' (100%). Ready for HR review in the verification queue.",
                    entity_id=task.id,
                    dedup_key_prefix=f"task_verification_{task.id}_{datetime.utcnow().date()}",
                )
            # Phase 4.C: Notify manager
            assignee_u = db.query(User).filter(User.id == task.employee_id).first()
            if assignee_u and assignee_u.manager_id and assignee_u.manager_id != user.id:
                _notify_user(
                    db,
                    assignee_u.manager_id,
                    "Team Task Completed",
                    f"{user.name} completed task '{task.name}' (100%). Submitted for HR verification.",
                    notification_type="TEAM_TASK_COMPLETED",
                    entity_id=task.id,
                    dedup_key=f"mgr_task_comp_{assignee_u.manager_id}_{task.id}",
                    link_url="/manager/work-process",
                )

    if "work_update" in data and data["work_update"] is not None:
        update_text = str(data["work_update"]).strip()
        task.work_update = update_text
        if update_text:
            try:
                sem = analyze_communication(update_text)
                comm = Communication(
                    employee_id=task.employee_id,
                    text=update_text,
                    source="task_update",
                    sentiment_score=sem.get("sentiment_score", 0),
                    stress_keyword_score=sem.get("stress_keyword_score", 0),
                    timestamp=datetime.utcnow(),
                )
                db.add(comm)
            except Exception:
                pass

    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)

    log_audit(
        db,
        actor=user,
        action="TASK_PROGRESS_UPDATED",
        target_type="task",
        target_id=task.id,
        old_value={"status": old_status, "progress": old_progress},
        new_value={"status": task.status, "progress": task.completion_percentage, "verification_status": task.verification_status},
    )

    pred = None
    assignee = db.query(User).filter(User.id == task.employee_id).first()
    if assignee:
        try:
            from .burnout_service import recalculate_employee_burnout
            pred = recalculate_employee_burnout(db, assignee.id, trigger_source="task_progress_update", actor=user, persist=True)
        except Exception:
            pass

    return task, pred


def update_task_status(db: Session, task_id: int, status: str, user: User) -> tuple[Task, dict | None]:
    """Compatibility function mapping status string updates to progress and authoritative status."""
    progress_map = {
        "Not Started": 0,
        "In Progress": 50,
        "Almost Completed": 90,
        "Completed": 100,
    }
    p = progress_map.get(status, 50)
    return update_task_details(db, task_id, {"progress": p}, user)


# ============================================================================
# PHASE 6 & 7: BLOCKED TASK UNBLOCK REQUEST WORKFLOW
# ============================================================================

def create_unblock_request(db: Session, task_id: int, user: User, data: dict) -> TaskUnblockRequest:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError("Task not found.")

    if user.role == "employee" and task.employee_id != user.id:
        raise ValueError("Unauthorized: You can only submit unblock requests for your own tasks.")
    if user.role == "manager":
        assignee_u = db.query(User).filter(User.id == task.employee_id).first()
        if assignee_u and assignee_u.id != user.id and assignee_u.manager_id != user.id and assignee_u.manager_name != user.name:
            raise ValueError("Unauthorized: You can only submit unblock requests for your team.")

    if task.status != "Blocked":
        raise ValueError("Only Blocked tasks can submit an unblock request.")

    requested_new_deadline = str(data.get("requested_new_deadline", "")).strip()
    if not requested_new_deadline:
        raise ValueError("Requested new deadline is required.")

    req_due_date = _parse_deadline_to_date(requested_new_deadline)
    if req_due_date and req_due_date < date.today():
        raise ValueError("Requested new deadline must be today or a future date.")

    extension_reason = str(data.get("extension_reason", "")).strip()
    if not extension_reason:
        raise ValueError("Reason for requesting an extension is required.")

    work_completed = str(data.get("work_completed", "")).strip()
    remaining_work = str(data.get("remaining_work", "")).strip()
    if not work_completed or not remaining_work:
        raise ValueError("Work completed so far and remaining work are required.")

    # Prevent duplicate active requests
    active_req = (
        db.query(TaskUnblockRequest)
        .filter(
            TaskUnblockRequest.task_id == task.id,
            TaskUnblockRequest.status.in_(["Pending HR Review", "More Information Required"]),
        )
        .first()
    )
    if active_req:
        raise ValueError("An active unblock request is already pending review for this task.")

    unblock_req = TaskUnblockRequest(
        task_id=task.id,
        requester_id=user.id,
        requester_role=user.role,
        original_deadline=task.deadline or str(task.due_date),
        requested_new_deadline=requested_new_deadline,
        requested_due_date=req_due_date,
        blocking_reason=task.blocked_reason or data.get("blocking_reason", ""),
        extension_reason=extension_reason,
        work_completed=work_completed,
        remaining_work=remaining_work,
        supporting_notes=data.get("supporting_notes", ""),
        status="Pending HR Review",
        created_at=datetime.utcnow(),
    )
    db.add(unblock_req)
    db.commit()
    db.refresh(unblock_req)

    _notify_hr_users(
        db,
        title="Task Unblock Request Submitted",
        body=f"{user.name} ({user.role}) submitted an extension & unblock request for task '{task.name}'.",
        entity_type="unblock_request",
        entity_id=unblock_req.id,
        dedup_key_prefix=f"hr_unblock_{unblock_req.id}",
    )

    log_audit(
        db,
        actor=user,
        action="TASK_UNBLOCK_REQUESTED",
        target_type="task_unblock_request",
        target_id=unblock_req.id,
        new_value={
            "task_id": task.id,
            "requested_deadline": requested_new_deadline,
            "extension_reason": extension_reason,
        },
    )

    return unblock_req


def requester_reply_unblock_clarification(db: Session, request_id: int, user: User, reply_text: str) -> TaskUnblockRequest:
    req = db.query(TaskUnblockRequest).filter(TaskUnblockRequest.id == request_id).first()
    if not req:
        raise ValueError("Unblock request not found.")

    task = db.query(Task).filter(Task.id == req.task_id).first()
    if user.role == "employee" and req.requester_id != user.id:
        raise ValueError("Unauthorized: Only the requester can reply to clarification.")

    if req.status != "More Information Required":
        raise ValueError("Request is not currently awaiting clarification.")

    clean_reply = str(reply_text).strip()
    if not clean_reply:
        raise ValueError("Clarification response cannot be empty.")

    req.clarification_response = clean_reply
    req.clarification_responded_at = datetime.utcnow()
    req.status = "Pending HR Review"
    req.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(req)

    _notify_hr_users(
        db,
        title="Clarification Provided for Unblock Request",
        body=f"{user.name} provided requested clarification for task '{task.name if task else req.task_id}'.",
        entity_type="unblock_request",
        entity_id=req.id,
        dedup_key_prefix=f"hr_clarify_reply_{req.id}_{datetime.utcnow().date()}",
    )

    log_audit(
        db,
        actor=user,
        action="TASK_UNBLOCK_CLARIFICATION_REPLIED",
        target_type="task_unblock_request",
        target_id=req.id,
        new_value={"clarification_response": clean_reply, "status": "Pending HR Review"},
    )

    return req


def get_unblock_requests_for_hr(db: Session) -> list[dict]:
    requests = (
        db.query(TaskUnblockRequest)
        .order_by(TaskUnblockRequest.id.desc())
        .all()
    )
    user_map = {u.id: u for u in db.query(User).all()}
    task_map = {t.id: t for t in db.query(Task).all()}

    res = []
    for r in requests:
        task = task_map.get(r.task_id)
        requester = user_map.get(r.requester_id)
        reviewer = user_map.get(r.reviewed_by_id) if r.reviewed_by_id else None

        res.append({
            "id": r.id,
            "task_id": f"T-{r.task_id}",
            "raw_task_id": r.task_id,
            "task_title": task.name if task else "Unknown Task",
            "task_progress": task.completion_percentage if task else 0,
            "task_status": task.status if task else "Blocked",
            "requester_id": requester.employee_code if requester else f"E{r.requester_id}",
            "requester_name": requester.name if requester else "Unknown",
            "requester_role": requester.role if requester else r.requester_role,
            "department": requester.department if requester else "General",
            "original_deadline": r.original_deadline or "—",
            "requested_new_deadline": r.requested_new_deadline,
            "blocking_reason": r.blocking_reason or (task.blocked_reason if task else "") or "—",
            "extension_reason": r.extension_reason,
            "work_completed": r.work_completed,
            "remaining_work": r.remaining_work,
            "supporting_notes": r.supporting_notes or "",
            "status": r.status,
            "clarification_requested": r.clarification_requested,
            "clarification_requested_at": r.clarification_requested_at.strftime("%d %b %Y, %I:%M %p") if r.clarification_requested_at else None,
            "clarification_response": r.clarification_response,
            "clarification_responded_at": r.clarification_responded_at.strftime("%d %b %Y, %I:%M %p") if r.clarification_responded_at else None,
            "decision_reason": r.decision_reason,
            "reviewed_by": reviewer.name if reviewer else None,
            "reviewed_at": r.reviewed_at.strftime("%d %b %Y, %I:%M %p") if r.reviewed_at else None,
            "created_at": r.created_at.strftime("%d %b %Y, %I:%M %p") if r.created_at else "",
        })
    return res


def hr_approve_unblock_request(db: Session, request_id: int, hr_user: User, data: dict) -> TaskUnblockRequest:
    if hr_user.role != "hr":
        raise ValueError("Unauthorized: Only HR can approve unblock requests.")

    req = db.query(TaskUnblockRequest).filter(TaskUnblockRequest.id == request_id).first()
    if not req:
        raise ValueError("Unblock request not found.")

    if req.status not in ("Pending HR Review", "More Information Required"):
        raise ValueError(f"Request is not eligible for approval (current status: {req.status}).")

    task = db.query(Task).filter(Task.id == req.task_id).first()
    if not task:
        raise ValueError("Associated task not found.")

    # 1. Update task deadline
    task.deadline = req.requested_new_deadline
    if req.requested_due_date:
        task.due_date = req.requested_due_date
    elif req.requested_new_deadline:
        task.due_date = _parse_deadline_to_date(req.requested_new_deadline)

    # 2. Unblock task: derive new status from existing progress
    task.blocked_reason = None
    task.missed_deadline_at = None
    new_status = derive_task_status_from_progress(task.completion_percentage or 0)
    task.status = new_status
    task.updated_at = datetime.utcnow()

    # 3. Update request record
    reason = str(data.get("reason", "Approved extension by HR")).strip()
    req.status = "Approved"
    req.reviewed_by_id = hr_user.id
    req.reviewed_at = datetime.utcnow()
    req.decision_reason = reason
    req.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(req)
    db.refresh(task)

    # 4. Notify requester
    _notify_user(
        db,
        req.requester_id,
        "Task Unblocked & Extension Approved",
        f"HR approved your extension for '{task.name}' to {req.requested_new_deadline}. Task status is now {task.status}.",
        notification_type="UNBLOCK_APPROVED",
        entity_type="task",
        entity_id=task.id,
        dedup_key=f"unblock_appr_{req.id}",
        priority="high",
        link_url="/employee/work" if req.requester_role == "employee" else "/manager/work-process",
    )

    log_audit(
        db,
        actor=hr_user,
        action="TASK_UNBLOCK_APPROVED",
        target_type="task_unblock_request",
        target_id=req.id,
        new_value={
            "task_id": task.id,
            "new_deadline": task.deadline,
            "new_status": task.status,
            "reason": reason,
        },
    )

    # 5. Trigger burnout prediction recalculation
    target_emp = db.query(User).filter(User.id == task.employee_id).first()
    if target_emp:
        try:
            from .burnout_service import predict_for_employee
            predict_for_employee(db, target_emp, persist=True)
        except Exception:
            pass

    return req


def hr_request_clarification(db: Session, request_id: int, hr_user: User, message: str) -> TaskUnblockRequest:
    if hr_user.role != "hr":
        raise ValueError("Unauthorized: Only HR can review unblock requests.")

    req = db.query(TaskUnblockRequest).filter(TaskUnblockRequest.id == request_id).first()
    if not req:
        raise ValueError("Unblock request not found.")

    if req.status not in ("Pending HR Review", "More Information Required"):
        raise ValueError(f"Request is not eligible for clarification (current status: {req.status}).")

    clean_msg = str(message).strip()
    if not clean_msg:
        raise ValueError("Clarification message is required.")

    req.clarification_requested = clean_msg
    req.clarification_requested_at = datetime.utcnow()
    req.status = "More Information Required"
    req.reviewed_by_id = hr_user.id
    req.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(req)

    task = db.query(Task).filter(Task.id == req.task_id).first()
    _notify_user(
        db,
        req.requester_id,
        "Unblock Request: More Information Required",
        f"HR requested more details for task '{task.name if task else req.task_id}': {clean_msg}",
        notification_type="UNBLOCK_CLARIFICATION_REQUESTED",
        entity_type="unblock_request",
        entity_id=req.id,
        dedup_key=f"unblock_clarify_req_{req.id}_{datetime.utcnow().date()}",
        priority="high",
        link_url="/employee/work" if req.requester_role == "employee" else "/manager/work-process",
    )

    log_audit(
        db,
        actor=hr_user,
        action="TASK_UNBLOCK_CLARIFICATION_REQUESTED",
        target_type="task_unblock_request",
        target_id=req.id,
        new_value={"clarification_message": clean_msg},
    )

    return req


def hr_reject_unblock_request(db: Session, request_id: int, hr_user: User, reason: str) -> TaskUnblockRequest:
    if hr_user.role != "hr":
        raise ValueError("Unauthorized: Only HR can reject unblock requests.")

    req = db.query(TaskUnblockRequest).filter(TaskUnblockRequest.id == request_id).first()
    if not req:
        raise ValueError("Unblock request not found.")

    if req.status not in ("Pending HR Review", "More Information Required"):
        raise ValueError(f"Request is not eligible for rejection (current status: {req.status}).")

    clean_reason = str(reason).strip()
    if not clean_reason:
        raise ValueError("Rejection reason is required.")

    req.status = "Rejected"
    req.reviewed_by_id = hr_user.id
    req.reviewed_at = datetime.utcnow()
    req.decision_reason = clean_reason
    req.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(req)

    task = db.query(Task).filter(Task.id == req.task_id).first()
    _notify_user(
        db,
        req.requester_id,
        "Unblock Request Rejected",
        f"HR rejected your unblock request for '{task.name if task else req.task_id}': {clean_reason}",
        notification_type="UNBLOCK_REJECTED",
        entity_type="unblock_request",
        entity_id=req.id,
        dedup_key=f"unblock_reject_{req.id}",
        priority="high",
        link_url="/employee/work" if req.requester_role == "employee" else "/manager/work-process",
    )

    log_audit(
        db,
        actor=hr_user,
        action="TASK_UNBLOCK_REJECTED",
        target_type="task_unblock_request",
        target_id=req.id,
        new_value={"reason": clean_reason},
    )

    return req


# ============================================================================
# PHASE 8: HR TASK VERIFICATION WORKFLOW
# ============================================================================

def get_tasks_for_verification_hr(db: Session) -> list[dict]:
    """Retrieves tasks that have reached 100% completion and require HR verification."""
    all_users = db.query(User).all()
    user_map = {u.id: u for u in all_users}

    tasks = (
        db.query(Task)
        .filter(Task.verification_status.in_(["Awaiting Verification", "Verified", "Changes Requested"]))
        .order_by(Task.completed_at.desc().nullslast(), Task.id.desc())
        .all()
    )

    rows = []
    for t in tasks:
        emp = user_map.get(t.employee_id)
        assigned_by = user_map.get(t.assigned_by_id) if t.assigned_by_id else None
        verified_by = user_map.get(t.verified_by_id) if t.verified_by_id else None

        rows.append({
            "id": f"T-{t.id}",
            "raw_id": t.id,
            "title": t.name,
            "name": t.name,
            "description": t.description or "",
            "priority": t.priority,
            "deadline": t.deadline or "Upcoming",
            "progress": t.completion_percentage or 0,
            "status": t.status,
            "work_update": t.work_update or "—",
            "completed_at": t.completed_at.strftime("%d %b %Y, %I:%M %p") if t.completed_at else "—",
            "employee_name": emp.name if emp else f"User {t.employee_id}",
            "employee_code": emp.employee_code if emp else f"E{t.employee_id}",
            "employee_role": emp.role if emp else "employee",
            "department": emp.department if emp else "Engineering",
            "assigned_by_name": t.assigned_by_name or (assigned_by.name if assigned_by else "Manager"),
            "verification_status": t.verification_status,
            "verified_by_name": verified_by.name if verified_by else None,
            "verified_at": t.verified_at.strftime("%d %b %Y, %I:%M %p") if t.verified_at else None,
            "verification_notes": t.verification_notes or "",
        })
    return rows


def hr_verify_task(db: Session, task_id: int, hr_user: User, notes: str | None = None) -> Task:
    if hr_user.role != "hr":
        raise ValueError("Unauthorized: Only HR can verify tasks.")

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError("Task not found.")

    if task.status != "Completed":
        raise ValueError("Only Completed tasks can be verified.")

    task.verification_status = "Verified"
    task.verified_by_id = hr_user.id
    task.verified_at = datetime.utcnow()
    task.verification_notes = str(notes).strip() if notes else "Verified by HR"
    task.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(task)

    # Phase 3.F: Notify employee
    _notify_user(
        db,
        task.employee_id,
        "Task Verified by HR",
        f"Your completed task '{task.name}' has been verified and signed off by HR.",
        notification_type="TASK_VERIFIED",
        entity_type="task",
        entity_id=task.id,
        dedup_key=f"task_verified_{task.id}",
        priority="high",
        link_url="/employee/work",
    )
    # Phase 4.A/C: Notify manager
    assignee_u = db.query(User).filter(User.id == task.employee_id).first()
    if assignee_u and assignee_u.manager_id:
        _notify_user(
            db,
            assignee_u.manager_id,
            "Team Task Verified",
            f"HR verified and completed task '{task.name}' for {assignee_u.name}.",
            notification_type="TEAM_TASK_VERIFIED",
            entity_type="task",
            entity_id=task.id,
            dedup_key=f"mgr_task_verified_{assignee_u.manager_id}_{task.id}",
            link_url="/manager/work-process",
        )

    log_audit(
        db,
        actor=hr_user,
        action="TASK_VERIFIED",
        target_type="task",
        target_id=task.id,
        new_value={"verification_status": "Verified", "notes": task.verification_notes},
    )

    try:
        from .burnout_service import recalculate_employee_burnout
        recalculate_employee_burnout(db, task.employee_id, trigger_source="task_verified", actor=hr_user, persist=True)
    except Exception:
        pass

    return task


def hr_request_task_changes(db: Session, task_id: int, hr_user: User, notes: str) -> Task:
    if hr_user.role != "hr":
        raise ValueError("Unauthorized: Only HR can request changes on completed tasks.")

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError("Task not found.")

    if task.verification_status not in ("Awaiting Verification", "Changes Requested") and task.status != "Completed":
        raise ValueError(f"Task is not eligible for requesting changes (current status: {task.status}, verification: {task.verification_status}).")

    clean_notes = str(notes).strip()
    if not clean_notes:
        raise ValueError("Please provide an explanation of required changes.")

    task.verification_status = "Changes Requested"
    task.verification_notes = clean_notes
    # Reopen task for updates
    task.status = "In Progress"
    task.completion_percentage = 90
    task.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(task)

    # Phase 3.E: Notify employee
    _notify_user(
        db,
        task.employee_id,
        "Task: Changes Requested",
        f"HR requested revisions on '{task.name}': {clean_notes}. Task has been reopened to 90% progress.",
        notification_type="TASK_CHANGES_REQUESTED",
        entity_type="task",
        entity_id=task.id,
        dedup_key=f"task_changes_{task.id}_{datetime.utcnow().date()}",
        priority="high",
        link_url="/employee/work",
    )
    # Phase 4.C: Notify manager
    assignee_u = db.query(User).filter(User.id == task.employee_id).first()
    if assignee_u and assignee_u.manager_id:
        _notify_user(
            db,
            assignee_u.manager_id,
            "Team Task: Changes Requested",
            f"HR requested revisions on completed task '{task.name}' for {assignee_u.name}.",
            notification_type="TEAM_TASK_CHANGES_REQUESTED",
            entity_type="task",
            entity_id=task.id,
            dedup_key=f"mgr_task_changes_{assignee_u.manager_id}_{task.id}_{datetime.utcnow().date()}",
            link_url="/manager/work-process",
        )

    log_audit(
        db,
        actor=hr_user,
        action="TASK_CHANGES_REQUESTED",
        target_type="task",
        target_id=task.id,
        new_value={"verification_status": "Changes Requested", "notes": clean_notes, "status": "In Progress"},
    )

    # Recalculate burnout prediction for employee using central service (Part 2.2.B/C)
    target_emp = db.query(User).filter(User.id == task.employee_id).first()
    if target_emp:
        try:
            from .burnout_service import recalculate_employee_burnout
            recalculate_employee_burnout(db, target_emp.id, trigger_source="task_changes_requested", actor=hr_user, persist=True)
        except Exception:
            pass

    return task


def get_team_workload_metrics(db: Session, manager_user: User) -> dict:
    check_and_block_overdue_tasks(db)

    from .burnout_service import get_employee_core_metrics, get_employees_core_metrics_batch

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

    u_core = get_employees_core_metrics_batch(db, team_members)

    rows = []
    all_team_tasks = []
    total_assigned = 0
    total_completed = 0
    total_pending = 0
    total_blocked = 0
    total_overdue = 0

    for m in team_members:
        tasks = db.query(Task).filter(Task.employee_id == m.id).all()
        assigned = len(tasks)
        completed = sum(1 for t in tasks if t.status in ("Completed", "Done"))
        blocked = sum(1 for t in tasks if t.status == "Blocked" or (t.blocked_reason and t.status not in ("Completed", "Done")))
        overdue = sum(1 for t in tasks if t.status == "Overdue")
        pending = sum(1 for t in tasks if t.status in ("Pending", "Not Started", "In Progress", "Almost Completed") and not (t.blocked_reason and t.status not in ("Completed", "Done")))

        total_assigned += assigned
        total_completed += completed
        total_pending += pending
        total_blocked += blocked
        total_overdue += overdue

        for t in tasks:
            all_team_tasks.append({
                "id": f"T-{t.id}",
                "raw_id": t.id,
                "employee": m.name,
                "employee_code": m.employee_code or f"E{m.id}",
                "department": m.department or "Engineering",
                "name": t.name,
                "description": t.description or "",
                "priority": t.priority,
                "deadline": t.deadline or "Upcoming",
                "status": t.status,
                "completion_percentage": t.completion_percentage or 0,
                "progress": t.completion_percentage or 0,
                "verification_status": t.verification_status or "None",
                "work_update": t.work_update or "—",
                "blocked_reason": t.blocked_reason or "—",
                "assigned_by": t.assigned_by_name or manager_user.name,
                "updated_at": t.updated_at.strftime("%d %b %Y, %I:%M %p") if t.updated_at else "—",
            })

        m_metrics = u_core.get(m.id) or get_employee_core_metrics(db, m)
        rows.append({
            "id": m.employee_code or f"E{m.id}",
            "raw_id": m.id,
            "employee": m.name,
            "department": m.department or "Engineering",
            "assigned": assigned,
            "completed": completed,
            "pending": pending,
            "blocked": blocked,
            "overdue": overdue,
            "workload": m_metrics["workload_score"] if m_metrics["workload_score"] is not None else 50,
        })

    valid_workloads = [r["workload"] for r in rows if r["workload"] is not None]
    avg_workload = round(sum(valid_workloads) / len(valid_workloads), 1) if valid_workloads else 0.0

    member_ids = [m.id for m in team_members]
    team_att = (
        db.query(Attendance)
        .filter(Attendance.employee_id.in_(member_ids), Attendance.working_minutes > 0)
        .order_by(Attendance.date.desc())
        .limit(max(len(member_ids) * 7, 14))
        .all()
    ) if member_ids else []
    avg_hours = round(sum(a.working_minutes for a in team_att) / len(team_att) / 60.0, 1) if team_att else 8.0

    completion_rate = round(100 * total_completed / max(total_assigned, 1)) if total_assigned else 0

    today_d = date.today()
    monday = today_d - timedelta(days=today_d.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(5)]
    week_att_rows = (
        db.query(Attendance)
        .filter(Attendance.employee_id.in_(member_ids), Attendance.date.in_(week_dates))
        .all()
    ) if member_ids else []
    week_att_by_date = {}
    for a in week_att_rows:
        week_att_by_date.setdefault(a.date, []).append(a)

    hours_week = []
    days_names = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    for i, wd in enumerate(week_dates):
        d_atts = week_att_by_date.get(wd, [])
        valid_m = [a.working_minutes for a in d_atts if a.working_minutes and a.working_minutes > 0]
        ot_m = [a.overtime_minutes for a in d_atts if a.overtime_minutes and a.overtime_minutes > 0]
        h = round(sum(valid_m) / len(valid_m) / 60.0, 1) if valid_m else 0.0
        ot = round(sum(ot_m) / len(ot_m) / 60.0, 1) if ot_m else 0.0
        hours_week.append({"day": days_names[i], "hours": h, "ot": ot})

    team_surveys = (
        db.query(Survey)
        .filter(Survey.employee_id.in_(member_ids), Survey.date == today_d)
        .all()
    ) if member_ids else []
    exp_wl_list = [float(s.answers["manageable"]) for s in team_surveys if s.answers and "manageable" in s.answers]
    act_wl_list = [float(s.answers["workload"]) for s in team_surveys if s.answers and "workload" in s.answers]
    stress_list = [float(s.answers["stress"]) for s in team_surveys if s.answers and "stress" in s.answers]

    expected_actual = [
        {"metric": "Workload", "expected": round(sum(exp_wl_list) / len(exp_wl_list)) if exp_wl_list else 3, "actual": round(sum(act_wl_list) / len(act_wl_list)) if act_wl_list else 3},
        {"metric": "Stress", "expected": 2, "actual": round(sum(stress_list) / len(stress_list)) if stress_list else 2},
        {"metric": "Difficulty", "expected": 3, "actual": 3},
    ]

    return {
        "summary": {
            "assigned": total_assigned,
            "completed": total_completed,
            "pending": total_pending,
            "blocked": total_blocked,
            "overdue": total_overdue,
            "completion": completion_rate,
            "completion_rate": f"{completion_rate}%",
            "avgWorkload": avg_workload,
            "avgHours": avg_hours,
        },
        "members": rows,
        "tasks": all_team_tasks,
        "hoursWeek": hours_week,
        "weekly_hours": hours_week,
        "expectedActualToday": expected_actual,
    }


def get_all_organization_tasks_hr(db: Session) -> dict:
    check_and_block_overdue_tasks(db)

    all_users = db.query(User).all()
    user_map = {u.id: u for u in all_users}
    all_tasks = db.query(Task).order_by(Task.id.desc()).all()

    task_rows = []
    total_assigned = len(all_tasks)
    total_completed = 0
    total_pending = 0
    total_blocked = 0
    total_overdue = 0

    for t in all_tasks:
        emp = user_map.get(t.employee_id)
        if t.status == "Completed":
            total_completed += 1
        elif t.status == "Blocked":
            total_blocked += 1
        elif t.status in ("In Progress", "Pending", "Not Started", "Almost Completed"):
            total_pending += 1
        elif t.status == "Overdue":
            total_overdue += 1

        task_rows.append({
            "id": f"T-{t.id}",
            "raw_id": t.id,
            "name": t.name,
            "title": t.name,
            "description": t.description or "",
            "employee": emp.name if emp else f"User {t.employee_id}",
            "employee_id": emp.employee_code if emp else f"E{t.employee_id}",
            "department": emp.department if emp else "Engineering",
            "role": emp.role if emp else "employee",
            "priority": t.priority,
            "deadline": t.deadline or "Upcoming",
            "status": t.status,
            "progress": t.completion_percentage or 0,
            "verification_status": t.verification_status or "None",
            "work_update": t.work_update or "—",
            "blocked_reason": t.blocked_reason or "—",
            "assigned_by": t.assigned_by_name or (emp.manager_name if emp else "Manager"),
            "assigned_by_id": t.assigned_by_id,
            "created_at": t.created_at.strftime("%d %b %Y") if t.created_at else "—",
            "completed_at": t.completed_at.strftime("%d %b %Y") if t.completed_at else "—",
        })

    completion_rate = round(100 * total_completed / max(total_assigned, 1))
    return {
        "summary": {
            "assigned": total_assigned,
            "completed": total_completed,
            "pending": total_pending,
            "blocked": total_blocked,
            "overdue": total_overdue,
            "completion_rate": f"{completion_rate}%",
        },
        "tasks": task_rows,
    }
