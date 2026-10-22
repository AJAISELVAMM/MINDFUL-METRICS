from __future__ import annotations
from datetime import date, datetime, timedelta, time
from typing import Any
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from .config import ALLOWED_ORIGINS, FRONTEND_URL
from .database import Base, engine, get_db, SessionLocal
from .models import (
    User, Attendance, LeaveRequest, PermissionRequest, Task,
    Survey, PulseSurvey, Notification, Communication, Prediction,
    CompanySettings, Department, Intervention, BurnoutFeatures,
    TaskUnblockRequest
)
from .security import hash_password, verify_password, create_token, current_user, require_role
from .seed import seed
from .ml.model_loader import load_metadata
from .services.burnout_service import (
    ensure_trained, predict_for_employee, recalculate_employee_burnout,
    get_employee_core_metrics, get_employees_core_metrics_batch
)
from .services.semantic_service import analyze_communication
from .services.attendance_service import (
    check_in_user, check_out_user, get_today_attendance_record,
    get_user_attendance_history, get_company_settings, get_current_time, calculate_attendance_rule,
    finalize_daily_attendance, create_attendance_correction_request,
    get_attendance_corrections, approve_attendance_correction, reject_attendance_correction,
    get_attendance_summary_metrics, get_attendance_calendar_feed, recover_missed_finalizations,
    get_canonical_attendance_status
)
from .services.holiday_service import (
    get_all_holidays, generate_sundays_calendar, seed_2027_holidays, seed_all_holidays
)
from .services.leave_service import (
    apply_leave, get_my_leaves, get_team_leaves, get_all_leaves_hr, update_leave_status, cancel_leave
)
from .services.permission_service import (
    apply_permission, get_my_permissions, get_team_permissions,
    get_all_permissions_hr, update_permission_status, cancel_permission
)
from .services.survey_service import (
    get_survey_questions_for_role, submit_daily_survey,
    submit_pulse_survey, get_today_survey_status
)
from .services.task_service import (
    get_user_tasks, create_task, update_task_status, update_task_details,
    get_team_workload_metrics, get_all_organization_tasks_hr,
    create_unblock_request, requester_reply_unblock_clarification,
    get_unblock_requests_for_hr, hr_approve_unblock_request,
    hr_request_clarification, hr_reject_unblock_request,
    get_tasks_for_verification_hr, hr_verify_task, hr_request_task_changes,
    derive_task_status_from_progress, check_and_block_overdue_tasks,
)
from .services.audit_service import log_audit
from .services.ai_chat_service import process_chat_request
from .services.notification_service import (
    create_notification, get_user_notifications, get_unread_count,
    mark_notification_as_read, mark_all_as_read, archive_notification,
    run_notification_retention_cleanup, check_and_generate_deadline_reminders,
)

ALIASES = {
    "employee@workwell.com": "employee@mindfulmetrics.com",
    "manager@workwell.com": "manager@mindfulmetrics.com",
    "hr@workwell.com": "hr@mindfulmetrics.com",
}

app = FastAPI(title="Mindful Metrics API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS + [
        FRONTEND_URL,
        "https://mindful-metrics-alpha.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https://.*(\.trycloudflare\.com|\.vercel\.app)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def ensure_schema():
    if not str(engine.url).startswith("sqlite"):
        return
    with engine.connect() as conn:
        try:
            res = conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
            cols = [r[1] for r in res]
            if "phone" not in cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN phone VARCHAR(40) DEFAULT '+91 98765 43210'")
            if "avatar" not in cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN avatar TEXT")

            t_res = conn.exec_driver_sql("PRAGMA table_info(tasks)").fetchall()
            t_cols = [r[1] for r in t_res]
            if "assigned_by_id" not in t_cols:
                conn.exec_driver_sql("ALTER TABLE tasks ADD COLUMN assigned_by_id INTEGER")
            if "assigned_by_name" not in t_cols:
                conn.exec_driver_sql("ALTER TABLE tasks ADD COLUMN assigned_by_name VARCHAR(120)")
            if "work_update" not in t_cols:
                conn.exec_driver_sql("ALTER TABLE tasks ADD COLUMN work_update TEXT")
            if "completed_at" not in t_cols:
                conn.exec_driver_sql("ALTER TABLE tasks ADD COLUMN completed_at DATETIME")
            if "start_date" not in t_cols:
                conn.exec_driver_sql("ALTER TABLE tasks ADD COLUMN start_date DATE")
            if "due_date" not in t_cols:
                conn.exec_driver_sql("ALTER TABLE tasks ADD COLUMN due_date DATE")

            a_res = conn.exec_driver_sql("PRAGMA table_info(attendance)").fetchall()
            a_cols = [r[1] for r in a_res]
            if "arrival_status" not in a_cols:
                conn.exec_driver_sql("ALTER TABLE attendance ADD COLUMN arrival_status VARCHAR(20) DEFAULT 'ON_TIME'")
            if "attendance_day_value" not in a_cols:
                conn.exec_driver_sql("ALTER TABLE attendance ADD COLUMN attendance_day_value FLOAT DEFAULT 1.0")
            if "finalized_at" not in a_cols:
                conn.exec_driver_sql("ALTER TABLE attendance ADD COLUMN finalized_at TIMESTAMP NULL")
            conn.commit()
        except Exception:
            pass

try:
    ensure_schema()
except Exception as _e:
    pass


async def attendance_scheduler_loop():
    """
    Background scheduler running inside FastAPI.
    - Runs check_and_block_overdue_tasks periodically to enforce task deadlines idempotently.
    - Checks if local time in Asia/Kolkata is at or past 19:00 (7 PM) to finalize daily attendance.
    - Offloaded to worker thread via anyio to keep event loop 100% non-blocking.
    """
    import asyncio
    import anyio
    last_finalized_date = None

    def _sync_scheduler_step():
        nonlocal last_finalized_date
        from .services.attendance_service import get_company_settings, get_current_time, finalize_daily_attendance
        from .services.task_service import check_and_block_overdue_tasks
        from .database import SessionLocal

        db = SessionLocal()
        try:
            check_and_block_overdue_tasks(db)
            settings = get_company_settings(db)
            now = get_current_time(settings.timezone)
            today = now.date()

            if now.hour >= 19 and last_finalized_date != today:
                print(f"[SCHEDULER] Triggering 7:00 PM daily attendance finalization for {today}...")
                res = finalize_daily_attendance(db, target_date=today)
                print(f"[SCHEDULER] 7 PM finalization completed: {res}")
                last_finalized_date = today
        finally:
            db.close()

    while True:
        try:
            await asyncio.sleep(60)
            await anyio.to_thread.run_sync(_sync_scheduler_step)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print("[SCHEDULER ERROR]", e)


@app.on_event("startup")
def startup():
    try:
        ensure_schema()
        Base.metadata.create_all(bind=engine)
        ensure_trained()
        db = SessionLocal()
        try:
            seed(db)
            seed_all_holidays(db)
            blocked_count = check_and_block_overdue_tasks(db)
            if blocked_count > 0:
                print(f"[STARTUP] Automatically blocked {blocked_count} overdue tasks.")
        finally:
            db.close()
    except Exception as e:
        print("[STARTUP WARNING]", e)
    import asyncio
    import anyio

    async def async_startup_recovery():
        await asyncio.sleep(2)
        def _sync_recovery():
            r_db = SessionLocal()
            try:
                return recover_missed_finalizations(r_db, max_days_back=7)
            finally:
                r_db.close()

        try:
            rec_res = await anyio.to_thread.run_sync(_sync_recovery)
            if rec_res.get("recovered_count", 0) > 0:
                print(f"[STARTUP RECOVERY] Recovered missed attendance for {rec_res['recovered_count']} past dates.")
        except Exception as e:
            print("[STARTUP RECOVERY WARNING]", e)

    asyncio.create_task(async_startup_recovery())
    asyncio.create_task(attendance_scheduler_loop())


@app.get("/")
def root():
    return {"service": "Mindful Metrics API", "docs": "/docs", "health": "/api/health"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/health")
def api_health():
    return {"ok": True, "status": "ok", "product": "Mindful Metrics"}


# ===============================================================
# SCHEMAS
# ===============================================================

class LoginIn(BaseModel):
    email: str
    password: str


class SurveyIn(BaseModel):
    answers: dict
    note: str | None = None


class CheckInIn(BaseModel):
    answers: dict | None = None


class CheckOutIn(BaseModel):
    answers: dict | None = None
    note: str | None = None


class PulseIn(BaseModel):
    workload: str


class LeaveIn(BaseModel):
    type: str = "Casual Leave"
    leave_type: str | None = None
    date: str = ""
    duration: str = "1 day"
    half_day_session: str = "FULL_DAY"
    reason: str = ""
    start: str | None = None
    end: str | None = None


class PermissionIn(BaseModel):
    date: str | None = None
    requested_checkout_time: str = "04:30 PM"
    reason: str = ""


class TaskIn(BaseModel):
    name: str | None = None
    title: str | None = None
    description: str | None = None
    priority: str = "Medium"
    deadline: str = "Upcoming"
    difficulty: int = 3
    status: str = "Pending"
    progress: int | None = 0
    employee_id: Any | None = None
    assigned_to: Any | None = None
    work_update: str | None = None
    blocked_reason: str | None = None


class TaskUpdateIn(BaseModel):
    name: str | None = None
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    deadline: str | None = None
    status: str | None = None
    progress: int | None = None
    completion_percentage: int | None = None
    work_update: str | None = None
    blocked_reason: str | None = None
    difficulty: int | None = None


class TaskUnblockIn(BaseModel):
    requested_new_deadline: str
    extension_reason: str
    work_completed: str
    remaining_work: str
    supporting_notes: str | None = None
    blocking_reason: str | None = None


class TaskUnblockClarifyIn(BaseModel):
    message: str


class TaskUnblockReplyIn(BaseModel):
    response: str


class TaskUnblockDecisionIn(BaseModel):
    reason: str = "Approved by HR"


class TaskVerifyIn(BaseModel):
    notes: str | None = None


class TaskRequestChangesIn(BaseModel):
    notes: str


class InterventionIn(BaseModel):
    employee_id: Any
    risk_level: str = "High"
    trigger_reason: str = ""
    intervention_type: str = "Workload Review"
    recommendation: str | None = None
    status: str = "OPEN"
    follow_up_date: str | None = None
    notes: str | None = None
    resolution: str | None = None


class InterventionUpdateIn(BaseModel):
    status: str | None = None
    notes: str | None = None
    resolution: str | None = None
    follow_up_date: str | None = None
    intervention_type: str | None = None
    recommendation: str | None = None
    risk_level: str | None = None


class ChatIn(BaseModel):
    text: str | None = None
    message: str | None = None
    role: str | None = None
    page_context: dict[str, Any] | None = None
    conversation_history: list[dict[str, Any]] | None = None

    @property
    def query_text(self) -> str:
        return (self.text or self.message or "").strip()


class TextIn(BaseModel):
    text: str


class StatusIn(BaseModel):
    status: str


class SettingsIn(BaseModel):
    work_start_time: str | None = None
    checkin_grace_time: str | None = None
    afternoon_start_time: str | None = None
    early_checkout_threshold: str | None = None
    work_end_time: str | None = None
    timezone: str | None = None


class AttendanceCorrectionIn(BaseModel):
    attendance_date: str
    reason: str
    requested_status: str | None = "FULL_DAY_PRESENT"
    requested_check_in: str | None = "09:00 AM"
    requested_check_out: str | None = "05:30 PM"


class CorrectionReviewIn(BaseModel):
    rejection_reason: str | None = None


class FinalizeDailyIn(BaseModel):
    date: str | None = None
    force: bool = False


class UserUpdateIn(BaseModel):
    name: str | None = None
    phone: str | None = None
    department: str | None = None


class AvatarIn(BaseModel):
    avatar: str | None = None


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str


# ===============================================================
# AUTHENTICATION & USER PROFILE
# ===============================================================

@app.post("/api/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    email = ALIASES.get(body.email.strip().lower(), body.email.strip().lower())
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    token = create_token(user)
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "name": user.name,
            "department": user.department,
            "employeeId": user.employee_code,
            "phone": user.phone or "+91 98765 43210",
            "avatar": user.avatar or None,
        },
    }


@app.post("/api/auth/logout")
def logout(user: User = Depends(current_user)):
    return {"ok": True, "message": "Successfully logged out"}


@app.get("/api/auth/me")
@app.get("/api/user/profile")
def me(user: User = Depends(current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "name": user.name,
        "department": user.department,
        "employeeId": user.employee_code,
        "manager": user.manager_name,
        "phone": user.phone or "+91 98765 43210",
        "avatar": user.avatar or None,
    }


@app.put("/api/user/profile")
def update_profile(body: UserUpdateIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.name is not None and body.name.strip():
        user.name = body.name.strip()
    if body.phone is not None:
        user.phone = body.phone.strip()
    if body.department is not None and body.department.strip():
        user.department = body.department.strip()
    db.commit()
    db.refresh(user)
    return {
        "ok": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "name": user.name,
            "department": user.department,
            "employeeId": user.employee_code,
            "manager": user.manager_name,
            "phone": user.phone or "+91 98765 43210",
            "avatar": user.avatar or None,
        },
    }


@app.post("/api/user/avatar")
def update_avatar(body: AvatarIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.avatar = body.avatar if (body.avatar and body.avatar.strip()) else None
    db.commit()
    db.refresh(user)
    return {"ok": True, "avatar": user.avatar}


@app.delete("/api/user/avatar")
def delete_avatar(user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.avatar = None
    db.commit()
    db.refresh(user)
    return {"ok": True, "avatar": None}


@app.post("/api/auth/change-password")
@app.post("/api/user/change-password")
def change_password(body: PasswordChangeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    if len(body.new_password) < 6:
        raise HTTPException(400, "New password must be at least 6 characters")
    if body.current_password == body.new_password:
        raise HTTPException(400, "New password cannot be the same as current password")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True, "message": "Password changed successfully"}


# ===============================================================
# REAL KPI & CHART HELPERS
# ===============================================================

def _kpis_for(user: User, db: Session) -> dict:
    metrics = get_employee_core_metrics(db, user)
    burnout = metrics["burnout_score"]
    level = metrics["risk_level"]
    stress = metrics["stress_score"]
    workload = metrics["workload_score"]
    wlb = metrics["wlb_score"]
    wh_display = metrics["working_hours_display"] or "—"
    wh_num = metrics["working_hours_num"]

    return {
        "burnoutRisk": burnout if burnout is not None else "—",
        "burnoutLabel": level.title() if isinstance(level, str) else "Moderate",
        "stressScore": stress if stress is not None else "—",
        "stressLabel": "Elevated" if (stress or 0) >= 60 else "Moderate" if (stress or 0) >= 40 else "Stable",
        "workloadScore": workload if workload is not None else "—",
        "workloadLabel": "High" if (workload or 0) >= 70 else "Manageable" if (workload or 0) >= 40 else "Low",
        "wlbScore": wlb if wlb is not None else "—",
        "wlbLabel": "Optimal" if (wlb or 0) >= 70 else "Adequate" if (wlb or 0) >= 40 else "Strained",
        "workingHours": wh_display,
        "workingHoursNum": wh_num,
        "activeTasks": metrics["active_tasks"],
        "completedTasks": metrics["completed_tasks"],
        "totalTasks": metrics["total_tasks"],
        "completionRate": metrics["completion_rate"],
        "blockedTasks": metrics["blocked_tasks"],
    }


def _get_user_charts_data(user: User, db: Session) -> dict:
    today = date.today()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]

    # Real Hours Week from actual Attendance records
    att_rows = (
        db.query(Attendance)
        .filter(Attendance.employee_id == user.id, Attendance.date >= days[0], Attendance.date <= days[-1])
        .all()
    )
    att_by_date = {a.date: a for a in att_rows}

    hours_week = []
    for d in days:
        day_name = d.strftime("%a")
        rec = att_by_date.get(d)
        if rec and rec.working_minutes:
            h = round(rec.working_minutes / 60, 1)
            ot = round((rec.overtime_minutes or 0) / 60, 1)
        else:
            h = 0.0
            ot = 0.0
        hours_week.append({"day": day_name, "hours": h, "ot": ot})

    # Real Burnout Trend from actual Prediction records (mapped strictly to 7 days)
    all_user_preds = (
        db.query(Prediction)
        .filter(Prediction.employee_id == user.id)
        .order_by(Prediction.id.asc())
        .all()
    )
    preds_by_date = {}
    for p in all_user_preds:
        if p.prediction_date:
            preds_by_date[p.prediction_date.date()] = p

    last_val = 50
    burnout_trend = []
    for d in days:
        if d in preds_by_date:
            last_val = round(preds_by_date[d].burnout_score) if preds_by_date[d].burnout_score is not None else last_val
        burnout_trend.append({"day": d.strftime("%a"), "value": last_val})

    # Real Stress & Workload Trend from actual Survey records
    surveys = (
        db.query(Survey)
        .filter(Survey.employee_id == user.id, Survey.date >= days[0], Survey.date <= days[-1])
        .order_by(Survey.date.asc())
        .all()
    )
    if not surveys:
        surveys = (
            db.query(Survey)
            .filter(Survey.employee_id == user.id)
            .order_by(Survey.date.desc())
            .limit(7)
            .all()
        )
        surveys = list(reversed(surveys))

    stress_trend = []
    for s in surveys:
        ans = s.answers or {}
        st = ans.get("stress", 3)
        wl = ans.get("workload", ans.get("manageable", 3))
        try:
            st_sc = round(float(st) * 20)
            wl_sc = round(float(wl) * 20)
        except Exception:
            st_sc, wl_sc = 50, 50
        stress_trend.append({"day": s.date.strftime("%a"), "stress": st_sc, "workload": wl_sc})

    # Expected vs Actual from today's real survey
    today_survey = (
        db.query(Survey)
        .filter(Survey.employee_id == user.id, Survey.date == today)
        .first()
    )
    ans = today_survey.answers if today_survey and today_survey.answers else {}
    ea = [
        {"metric": "Workload", "expected": int(ans.get("manageable", 3)), "actual": int(ans.get("workload", ans.get("manageable", 3)))},
        {"metric": "Stress", "expected": 2, "actual": int(ans.get("stress", 3))},
        {"metric": "Difficulty", "expected": 3, "actual": int(ans.get("difficulty", 3))},
    ]

    return {
        "burnoutTrend7": burnout_trend,
        "hoursWeek": hours_week,
        "stressTrend": stress_trend,
        "expectedActualToday": ea,
    }


# ===============================================================
# EMPLOYEE DASHBOARD & DETAILS
# ===============================================================

@app.get("/api/employee/dashboard")
def emp_dash(user: User = Depends(require_role("employee", "manager", "hr")), db: Session = Depends(get_db)):
    charts = _get_user_charts_data(user, db)
    return {
        "employee": {
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "department": user.department,
            "employeeId": user.employee_code,
            "manager": user.manager_name,
        },
        "kpis": _kpis_for(user, db),
        **charts,
    }


@app.get("/api/employee/burnout")
@app.get("/api/burnout/current")
def emp_burn(user: User = Depends(current_user), db: Session = Depends(get_db)):
    pred = predict_for_employee(db, user, persist=True)
    charts = _get_user_charts_data(user, db)
    factors = pred.get("risk_factors") or []
    nf = [{"name": f.get("feature", f.get("name")), "value": round((f.get("importance") or 0) * 100)} for f in factors]
    return {
        "kpis": _kpis_for(user, db),
        "factors": nf,
        "burnoutTrend7": charts["burnoutTrend7"],
        "stressTrend": charts["stressTrend"],
        "expectedActualToday": charts["expectedActualToday"],
        "prediction": pred,
        "explanation": pred.get("explanation"),
        "insufficient_data": pred.get("insufficient_data", False),
    }


@app.get("/api/employee/trends")
@app.get("/api/burnout/trend")
def emp_tr(user: User = Depends(current_user), db: Session = Depends(get_db)):
    charts = _get_user_charts_data(user, db)
    return {
        "burnoutTrend7": charts["burnoutTrend7"],
        "hoursWeek": charts["hoursWeek"],
        "stressTrend": charts["stressTrend"],
        "expectedActualToday": charts["expectedActualToday"],
        "communicationSentiment": [
            {"week": "W1", "positive": 62, "neutral": 28, "negative": 10},
            {"week": "W2", "positive": 58, "neutral": 30, "negative": 12},
            {"week": "W3", "positive": 54, "neutral": 31, "negative": 15},
            {"week": "W4", "positive": 51, "neutral": 32, "negative": 17},
        ],
    }


def _categorize_rec(r: str) -> str:
    rl = r.lower()
    if any(k in rl for k in ("workload", "task", "priorit", "volume")):
        return "Workload"
    elif any(k in rl for k in ("overtime", "hour", "time", "clock")):
        return "Time Management"
    elif any(k in rl for k in ("after-hours", "balance", "wlb", "recovery", "evening")):
        return "Work-Life Balance"
    elif any(k in rl for k in ("manager", "communicat", "discuss", "collaborat", "sync")):
        return "Communication"
    else:
        return "Wellbeing"


@app.get("/api/employee/recommendations")
@app.get("/api/burnout/recommendations")
def recs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    last = db.query(Prediction).filter(Prediction.employee_id == user.id).order_by(Prediction.id.desc()).first()
    if not last:
        try:
            pred_gen = predict_for_employee(db, user, persist=True)
            if not pred_gen.get("insufficient_data"):
                last = db.query(Prediction).filter(Prediction.employee_id == user.id).order_by(Prediction.id.desc()).first()
        except Exception:
            pass

    recs_list = (last.recommendations if last else None)
    if not recs_list and last and last.top_factors:
        from .services.recommendation_service import recommendations_from_factors
        recs_list = recommendations_from_factors(last.top_factors, last.risk_level or "LOW")

    if recs_list:
        items = [{"category": _categorize_rec(r), "body": r} for r in recs_list if not r.startswith("These are")]
        if not items:
            items = [
                {"category": "Workload", "body": "Review task allocation and prioritize critical sprint items."},
                {"category": "Wellbeing", "body": "Take scheduled short breaks to reduce fatigue and reset focus."},
                {"category": "Communication", "body": "Discuss high-difficulty or blocked tasks with your manager."},
                {"category": "Work-Life Balance", "body": "Review after-hours workload patterns and prioritize recovery time."},
            ]
    else:
        items = [
            {"category": "Workload", "body": "Consider reviewing extended working hours and task distribution."},
            {"category": "Wellbeing", "body": "Take scheduled short breaks to reduce fatigue and reset focus."},
            {"category": "Communication", "body": "Discuss high-difficulty or blocked tasks with your manager."},
            {"category": "Work-Life Balance", "body": "Review after-hours workload patterns and prioritize recovery time."},
        ]
    return {"items": items, "risk": last.risk_level if last else "Moderate"}


# ===============================================================
# ATTENDANCE APIS (AUTHORITATIVE SERVER ENGINE)
# ===============================================================

@app.post("/api/attendance/check-in")
@app.post("/api/employee/check-in")
def check_in(
    body: CheckInIn | None = None,
    user: User = Depends(require_role("employee", "manager", "hr")),
    db: Session = Depends(get_db),
):
    survey_answers = body.answers if body else None
    res = check_in_user(db, user, survey_answers=survey_answers)
    if "error" in res:
        raise HTTPException(400, res["error"])
    return res


@app.post("/api/attendance/check-out")
@app.post("/api/employee/check-out")
def check_out(
    body: CheckOutIn | None = None,
    user: User = Depends(require_role("employee", "manager", "hr")),
    db: Session = Depends(get_db),
):
    survey_answers = body.answers if body else None
    note = body.note if body else None
    res = check_out_user(db, user, survey_answers=survey_answers, note=note)
    if "error" in res:
        raise HTTPException(400, res["error"])
    return res


@app.get("/api/attendance/today")
def att_today(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_today_attendance_record(db, user)


@app.get("/api/attendance/weekly")
@app.get("/api/employee/attendance")
def emp_att(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_user_attendance_history(db, user)


@app.get("/api/attendance/team")
@app.get("/api/manager/attendance")
def mgr_att(user: User = Depends(require_role("manager", "hr")), db: Session = Depends(get_db)):
    settings = get_company_settings(db)
    now = get_current_time(settings.timezone)
    today = now.date()
    from .services.holiday_service import is_holiday as check_holiday, is_weekly_off as check_sunday
    is_h, hol_obj = check_holiday(db, today, calendar_type="company")
    is_sunday = check_sunday(today)
    is_today_open = (now.time() < time(19, 0))

    if user.role == "hr":
        team_members = db.query(User).filter(User.role == "employee").all()
    else:
        team_members = (
            db.query(User)
            .filter(
                or_(
                    User.manager_name == user.name,
                    User.manager_id == user.id,
                )
            )
            .all()
        )
        if not team_members:
            team_members = db.query(User).filter(User.department == user.department, User.role == "employee").all()

    approved_leaves = db.query(LeaveRequest).filter(
        LeaveRequest.status == "Approved",
        or_(
            LeaveRequest.date.like(f"%{today}%"),
            (LeaveRequest.start_date <= today) & (LeaveRequest.end_date >= today),
        ),
    ).all()
    on_leave_users = {l.employee_id for l in approved_leaves}

    rows = []
    for m in team_members:
        rec = db.query(Attendance).filter(Attendance.employee_id == m.id, Attendance.date == today).first()
        h = rec.working_minutes // 60 if (rec and rec.working_minutes) else 0
        m_min = rec.working_minutes % 60 if (rec and rec.working_minutes) else 0
        hours_str = f"{h:02d}h {m_min:02d}m" if (rec and rec.working_minutes) else "—"
        canon_status, disp_status, _ = get_canonical_attendance_status(
            rec,
            is_holiday=is_h,
            is_weekly_off=is_sunday,
            has_leave=(m.id in on_leave_users),
            is_future=False,
            is_today_open=is_today_open,
        )
        rows.append({
            "name": m.name,
            "status": canon_status,
            "display_status": disp_status,
            "checkIn": rec.check_in if (rec and rec.check_in) else "—",
            "checkOut": rec.check_out if (rec and rec.check_out) else "—",
            "hours": hours_str,
        })
    return rows


@app.get("/api/attendance/all")
@app.get("/api/hr/attendance")
def hr_att(
    department: str | None = Query(None),
    status: str | None = Query(None),
    date_str: str | None = Query(None, alias="date"),
    user: User = Depends(require_role("hr")),
    db: Session = Depends(get_db),
):
    settings = get_company_settings(db)
    now = get_current_time(settings.timezone)
    today = now.date()
    target_d = today
    if date_str:
        try:
            target_d = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            target_d = today

    users_query = db.query(User).filter(User.role.in_(["employee", "manager"]))
    if department and department != "All":
        users_query = users_query.filter(User.department == department)
    all_users = users_query.all()

    target_atts = db.query(Attendance).filter(Attendance.date == target_d).all()
    att_by_user = {a.employee_id: a for a in target_atts}

    approved_leaves = db.query(LeaveRequest).filter(
        LeaveRequest.status == "Approved",
        or_(
            LeaveRequest.date.like(f"%{target_d}%"),
            (LeaveRequest.start_date <= target_d) & (LeaveRequest.end_date >= target_d),
        ),
    ).all()
    on_leave_users = {l.employee_id for l in approved_leaves}

    from .services.holiday_service import is_holiday as check_holiday, is_weekly_off as check_sunday
    is_h, hol_obj = check_holiday(db, target_d, calendar_type="company")
    is_sunday = check_sunday(target_d)
    is_future = target_d > today
    is_today_open = (target_d == today and now.time() < time(19, 0))

    rows = []
    for u in all_users:
        rec = att_by_user.get(u.id)
        has_approved_l = (u.id in on_leave_users)
        canon_status, disp_status, _ = get_canonical_attendance_status(
            rec,
            is_holiday=is_h,
            is_weekly_off=is_sunday,
            has_leave=has_approved_l,
            is_future=is_future,
            is_today_open=is_today_open,
        )
        h = rec.working_minutes // 60 if rec and rec.working_minutes else 0
        m = rec.working_minutes % 60 if rec and rec.working_minutes else 0

        if status and status != "All":
            s_up = status.upper()
            if s_up not in canon_status and status.lower() not in disp_status.lower():
                continue

        rows.append({
            "id": u.employee_code or f"E{u.id}",
            "name": u.name,
            "dept": u.department or "Engineering",
            "role": u.role or "employee",
            "status": canon_status,
            "display_status": disp_status,
            "checkIn": rec.check_in if (rec and rec.check_in) else "—",
            "checkOut": rec.check_out if (rec and rec.check_out) else "—",
            "hours": f"{h:02d}h {m:02d}m" if rec and rec.working_minutes else "—",
            "overtime": f"{rec.overtime_minutes // 60}h {rec.overtime_minutes % 60}m" if rec and rec.overtime_minutes else "—",
        })
    return rows



@app.get("/api/holidays")
def list_holidays(year: int = 2026, db: Session = Depends(get_db)):
    holidays = get_all_holidays(db, year=year)
    return [
        {
            "id": h.id,
            "holiday_name": h.holiday_name,
            "holiday_date": h.holiday_date.isoformat(),
            "holiday_type": h.holiday_type,
            "applicability": h.applicability,
            "source_name": h.source_name,
            "source_reference": h.source_reference,
            "source_verified": bool(h.source_verified),
        }
        for h in holidays
    ]


@app.get("/api/attendance/summary")
def get_attendance_summary(
    date_str: str | None = Query(None, alias="date"),
    year: int | None = Query(None),
    month: int | None = Query(None),
    department: str | None = Query(None),
    user_id: int | None = Query(None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role == "employee" and user_id and user_id != user.id:
        raise HTTPException(403, "Employees are only authorized to view their own attendance")
    if user.role == "manager" and user_id:
        target_user = db.query(User).filter(User.id == user_id).first()
        if target_user and target_user.department != user.department and target_user.id != user.id:
            raise HTTPException(403, "Managers can only access team member records within their department")
    target_dt = None
    if date_str:
        try:
            target_dt = date.fromisoformat(date_str.strip())
        except ValueError:
            raise HTTPException(400, "Invalid date format, expected YYYY-MM-DD")
    return get_attendance_summary_metrics(
        db=db,
        user=user,
        target_date=target_dt,
        year=year,
        month=month,
        department=department,
        target_user_id=user_id,
    )


@app.get("/api/attendance/calendar")
def get_attendance_calendar(
    year: int | None = Query(None),
    month: int | None = Query(None),
    user_id: int | None = Query(None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role == "employee" and user_id and user_id != user.id:
        raise HTTPException(403, "Employees are only authorized to view their own attendance")
    if user.role == "manager" and user_id:
        target_user = db.query(User).filter(User.id == user_id).first()
        if target_user and target_user.department != user.department and target_user.id != user.id:
            raise HTTPException(403, "Managers can only access team member records within their department")
    settings = get_company_settings(db)
    now = get_current_time(settings.timezone)
    y = year or now.year
    m = month or now.month
    if m < 1 or m > 12:
        raise HTTPException(400, "Month must be between 1 and 12")
    return get_attendance_calendar_feed(
        db=db,
        user=user,
        year=y,
        month=m,
        target_user_id=user_id,
    )


@app.get("/api/attendance/sundays")
def get_sundays_list(
    start_year: int = Query(2026),
    end_year: int = Query(2027),
):
    return generate_sundays_calendar(start_year=start_year, end_year=end_year)


@app.post("/api/attendance/holidays/seed-2027")
def seed_2027_holidays_endpoint(
    force_active: bool = Query(True),
    user: User = Depends(require_role("hr")),
    db: Session = Depends(get_db),
):
    return seed_2027_holidays(db, force_active=force_active)


@app.post("/api/attendance/recover")
def recover_attendance_endpoint(
    max_days: int = Query(14),
    user: User = Depends(require_role("hr", "manager")),
    db: Session = Depends(get_db),
):
    return recover_missed_finalizations(db, max_days_back=max_days)


@app.post("/api/attendance/finalize-daily")
def trigger_finalize_daily(
    body: FinalizeDailyIn | None = None,
    user: User = Depends(require_role("hr", "manager")),
    db: Session = Depends(get_db),
):
    target_dt = None
    force_val = body.force if body else False
    if body and body.date:
        try:
            target_dt = date.fromisoformat(body.date.strip())
        except ValueError:
            raise HTTPException(400, "Invalid date format, expected YYYY-MM-DD")
    res = finalize_daily_attendance(db, target_date=target_dt, force=force_val)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error", "Finalization failed"))
    return res


@app.post("/api/attendance/correction/request")
def request_attendance_correction(
    body: AttendanceCorrectionIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    try:
        att_dt = date.fromisoformat(body.attendance_date.strip())
    except ValueError:
        raise HTTPException(400, "Invalid date format, expected YYYY-MM-DD")

    res = create_attendance_correction_request(
        db,
        employee=user,
        attendance_date=att_dt,
        reason=body.reason,
        requested_status=body.requested_status or "FULL_DAY_PRESENT",
        requested_check_in=body.requested_check_in,
        requested_check_out=body.requested_check_out,
    )
    if "error" in res:
        raise HTTPException(400, res["error"])
    return res


@app.get("/api/attendance/correction/requests")
def list_attendance_corrections(
    status: str | None = Query(None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return get_attendance_corrections(db, user, status_filter=status)


@app.post("/api/attendance/correction/{correction_id}/approve")
def approve_correction(
    correction_id: int,
    user: User = Depends(require_role("hr")),
    db: Session = Depends(get_db),
):
    res = approve_attendance_correction(db, approver=user, correction_id=correction_id)
    if "error" in res:
        raise HTTPException(400, res["error"])
    return res


@app.post("/api/attendance/correction/{correction_id}/reject")
def reject_correction(
    correction_id: int,
    body: CorrectionReviewIn | None = None,
    user: User = Depends(require_role("hr")),
    db: Session = Depends(get_db),
):
    rejection_reason = body.rejection_reason if body else None
    res = reject_attendance_correction(db, approver=user, correction_id=correction_id, rejection_reason=rejection_reason)
    if "error" in res:
        raise HTTPException(400, res["error"])
    return res


# ===============================================================
# LEAVE MANAGEMENT APIS
# ===============================================================

@app.get("/api/leave/my")
@app.get("/api/employee/leaves")
def get_leaves(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_my_leaves(db, user)


@app.post("/api/leave")
@app.post("/api/employee/leaves")
def create_leave(body: LeaveIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    req = apply_leave(db, user, body.model_dump())
    return {
        "ok": True,
        "item": {
            "id": f"L-{req.id}",
            "date": req.date,
            "type": req.leave_type or req.type,
            "duration": req.duration,
            "reason": req.reason,
            "status": req.status,
        },
    }


@app.get("/api/leave/team")
@app.get("/api/manager/leave-requests")
def team_leaves(user: User = Depends(require_role("manager", "hr")), db: Session = Depends(get_db)):
    return get_team_leaves(db, user)


@app.get("/api/leave/all")
@app.get("/api/hr/leaves")
@app.get("/api/hr/leave")
def hr_leaves(
    employee: str | None = Query(None),
    department: str | None = Query(None),
    role: str | None = Query(None),
    leave_type: str | None = Query(None),
    status: str | None = Query(None),
    user: User = Depends(require_role("hr")),
    db: Session = Depends(get_db),
):
    return get_all_leaves_hr(
        db,
        employee=employee,
        department=department,
        role=role,
        leave_type=leave_type,
        status=status,
    )


@app.patch("/api/leave/{request_id}/approve")
def approve_leave_req(request_id: str, user: User = Depends(require_role("manager", "hr")), db: Session = Depends(get_db)):
    numeric_id = int(request_id.removeprefix("LR-").removeprefix("L-"))
    try:
        req = update_leave_status(db, numeric_id, "Approved", user)
        return {"ok": True, "id": request_id, "status": req.status}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.patch("/api/leave/{request_id}/reject")
def reject_leave_req(request_id: str, user: User = Depends(require_role("manager", "hr")), db: Session = Depends(get_db)):
    numeric_id = int(request_id.removeprefix("LR-").removeprefix("L-"))
    try:
        req = update_leave_status(db, numeric_id, "Rejected", user)
        return {"ok": True, "id": request_id, "status": req.status}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.patch("/api/manager/leave-requests/{request_id}")
def update_leave_endpoint(request_id: str, body: StatusIn, user: User = Depends(require_role("manager", "hr")), db: Session = Depends(get_db)):
    numeric_id = int(request_id.removeprefix("LR-").removeprefix("L-"))
    try:
        req = update_leave_status(db, numeric_id, body.status, user)
        return {"ok": True, "id": request_id, "status": req.status}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/leave/{request_id}")
@app.patch("/api/leave/{request_id}/cancel")
def cancel_leave_endpoint(request_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    numeric_id = int(request_id.removeprefix("LR-").removeprefix("L-"))
    try:
        req = cancel_leave(db, numeric_id, user)
        return {"ok": True, "id": request_id, "status": req.status}
    except ValueError as e:
        raise HTTPException(400, str(e))


# ===============================================================
# PERMISSION APIS
# ===============================================================

@app.post("/api/permission")
def create_permission(body: PermissionIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    req = apply_permission(db, user, body.model_dump())
    return {
        "ok": True,
        "item": {
            "id": f"PR-{req.id}",
            "date": req.date.strftime("%d %b %Y"),
            "requested_checkout_time": req.requested_checkout_time,
            "reason": req.reason,
            "status": req.status,
        },
    }


@app.get("/api/permission/my")
def my_permissions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_my_permissions(db, user)


@app.get("/api/permission/team")
def team_permissions(user: User = Depends(require_role("manager", "hr")), db: Session = Depends(get_db)):
    return get_team_permissions(db, user)


@app.get("/api/permission/all")
def all_permissions(user: User = Depends(require_role("hr")), db: Session = Depends(get_db)):
    return get_all_permissions_hr(db)


@app.patch("/api/permission/{perm_id}/approve")
def approve_permission_req(perm_id: str, user: User = Depends(require_role("manager", "hr")), db: Session = Depends(get_db)):
    numeric_id = int(perm_id.removeprefix("PR-"))
    try:
        req = update_permission_status(db, numeric_id, "Approved", user)
        return {"ok": True, "id": perm_id, "status": req.status}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.patch("/api/permission/{perm_id}/reject")
def reject_permission_req(perm_id: str, user: User = Depends(require_role("manager", "hr")), db: Session = Depends(get_db)):
    numeric_id = int(perm_id.removeprefix("PR-"))
    try:
        req = update_permission_status(db, numeric_id, "Rejected", user)
        return {"ok": True, "id": perm_id, "status": req.status}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/permission/{perm_id}")
@app.patch("/api/permission/{perm_id}/cancel")
def cancel_permission_endpoint(perm_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    numeric_id = int(perm_id.removeprefix("PR-"))
    try:
        req = cancel_permission(db, numeric_id, user)
        return {"ok": True, "id": perm_id, "status": req.status}
    except ValueError as e:
        raise HTTPException(400, str(e))


# ===============================================================
# SURVEY & PULSE APIS
# ===============================================================

@app.get("/api/survey/questions")
def survey_questions(user: User = Depends(current_user)):
    return get_survey_questions_for_role(user.role)


@app.get("/api/survey/today")
def survey_today(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_today_survey_status(db, user)


@app.post("/api/survey/daily")
@app.post("/api/employee/surveys")
def survey_submit(
    body: SurveyIn,
    survey_type: str = "daily",
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return submit_daily_survey(db, user, answers=body.answers, note=body.note, survey_type=survey_type)


@app.post("/api/survey/pulse")
def pulse_submit(body: PulseIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return submit_pulse_survey(db, user, body.workload)


# ===============================================================
# TASKS & WORKLOAD APIS
# ===============================================================

@app.get("/api/tasks")
@app.get("/api/tasks/my")
@app.get("/api/employee/work")
def get_tasks(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_user_tasks(db, user)


@app.post("/api/tasks")
def add_task(body: TaskIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        task = create_task(db, user, body.model_dump())
        return {
            "ok": True,
            "id": f"T-{task.id}",
            "name": task.name,
            "status": task.status,
            "priority": task.priority,
            "progress": task.completion_percentage,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/tasks/team")
def team_tasks(user: User = Depends(require_role("manager", "hr")), db: Session = Depends(get_db)):
    return get_team_workload_metrics(db, user)


@app.get("/api/tasks/all")
def org_tasks(user: User = Depends(require_role("hr")), db: Session = Depends(get_db)):
    return get_all_organization_tasks_hr(db)


@app.get("/api/tasks/{task_id}")
def get_single_task(task_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        numeric_id = int(task_id.removeprefix("T-"))
    except ValueError:
        raise HTTPException(400, "Invalid task id")
    task = db.query(Task).filter(Task.id == numeric_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    return {
        "id": f"T-{task.id}",
        "raw_id": task.id,
        "name": task.name,
        "description": task.description or "",
        "priority": task.priority,
        "deadline": task.deadline,
        "status": task.status,
        "progress": task.completion_percentage,
        "work_update": task.work_update or "",
        "blocked_reason": task.blocked_reason or "",
    }


@app.put("/api/tasks/{task_id}")
@app.patch("/api/tasks/{task_id}")
@app.patch("/api/employee/work/{task_id}")
def update_task_endpoint(task_id: str, body: TaskUpdateIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    clean_id = str(task_id).strip()
    if clean_id.startswith(("T-", "t-", "T_", "t_")):
        clean_id = clean_id[2:].strip()
    try:
        numeric_id = int(clean_id)
    except ValueError:
        raise HTTPException(400, f"Invalid task id: '{task_id}'")
    try:
        task, pred = update_task_details(db, numeric_id, body.model_dump(exclude_unset=True), user)
        return {
            "ok": True,
            "id": f"T-{task.id}",
            "raw_id": task.id,
            "status": task.status,
            "progress": task.completion_percentage,
            "verification_status": task.verification_status,
            "work_update": task.work_update,
            "blocked_reason": task.blocked_reason,
            "prediction": pred,
            "task": {
                "id": f"T-{task.id}",
                "raw_id": task.id,
                "status": task.status,
                "progress": task.completion_percentage,
                "verification_status": task.verification_status,
                "work_update": task.work_update,
                "blocked_reason": task.blocked_reason,
            },
        }
    except ValueError as e:
        db.rollback()
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(404, msg)
        elif "unauthorized" in msg.lower():
            raise HTTPException(403, msg)
        else:
            raise HTTPException(400, msg)
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Internal server error while saving task: {str(e)}")


@app.post("/api/tasks/{task_id}/updates")
def add_task_update_endpoint(task_id: str, body: TextIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        numeric_id = int(task_id.removeprefix("T-"))
    except ValueError:
        raise HTTPException(400, "Invalid task id")
    try:
        task, pred = update_task_details(db, numeric_id, {"work_update": body.text}, user)
        return {"ok": True, "id": task_id, "work_update": task.work_update, "prediction": pred}
    except ValueError as e:
        raise HTTPException(404, str(e))


# --- Unblock Request Endpoints ---

@app.post("/api/tasks/{task_id}/unblock-request")
def submit_unblock_request_endpoint(
    task_id: str,
    body: TaskUnblockIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    try:
        numeric_id = int(task_id.removeprefix("T-"))
    except ValueError:
        raise HTTPException(400, "Invalid task id")
    try:
        req = create_unblock_request(db, numeric_id, user, body.model_dump())
        return {
            "ok": True,
            "id": req.id,
            "task_id": task_id,
            "status": req.status,
            "requested_new_deadline": req.requested_new_deadline,
        }
    except ValueError as e:
        msg = str(e)
        if "unauthorized" in msg.lower():
            raise HTTPException(403, msg)
        raise HTTPException(400, msg)


@app.post("/api/tasks/{task_id}/unblock-request/reply")
@app.post("/api/tasks/unblock-requests/{request_id}/reply")
def reply_unblock_clarification_endpoint(
    body: TaskUnblockReplyIn,
    task_id: str | None = None,
    request_id: int | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    req_id = request_id
    if req_id is None and task_id:
        try:
            numeric_id = int(task_id.removeprefix("T-"))
            active_r = (
                db.query(TaskUnblockRequest)
                .filter(TaskUnblockRequest.task_id == numeric_id)
                .order_by(TaskUnblockRequest.id.desc())
                .first()
            )
            if active_r:
                req_id = active_r.id
        except ValueError:
            pass
    if not req_id:
        raise HTTPException(400, "Unblock request id required")
    try:
        req = requester_reply_unblock_clarification(db, req_id, user, body.response)
        return {
            "ok": True,
            "id": req.id,
            "status": req.status,
            "clarification_response": req.clarification_response,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/hr/tasks/unblock-requests")
def list_hr_unblock_requests(
    user: User = Depends(require_role("hr")),
    db: Session = Depends(get_db),
):
    return get_unblock_requests_for_hr(db)


@app.post("/api/hr/tasks/unblock-requests/{request_id}/approve")
def hr_approve_unblock(
    request_id: int,
    body: TaskUnblockDecisionIn,
    user: User = Depends(require_role("hr")),
    db: Session = Depends(get_db),
):
    try:
        req = hr_approve_unblock_request(db, request_id, user, body.model_dump())
        return {
            "ok": True,
            "id": req.id,
            "task_id": f"T-{req.task_id}",
            "status": req.status,
            "decision_reason": req.decision_reason,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/hr/tasks/unblock-requests/{request_id}/clarify")
def hr_clarify_unblock(
    request_id: int,
    body: TaskUnblockClarifyIn,
    user: User = Depends(require_role("hr")),
    db: Session = Depends(get_db),
):
    try:
        req = hr_request_clarification(db, request_id, user, body.message)
        return {
            "ok": True,
            "id": req.id,
            "status": req.status,
            "clarification_requested": req.clarification_requested,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/hr/tasks/unblock-requests/{request_id}/reject")
def hr_reject_unblock(
    request_id: int,
    body: TaskUnblockDecisionIn,
    user: User = Depends(require_role("hr")),
    db: Session = Depends(get_db),
):
    try:
        req = hr_reject_unblock_request(db, request_id, user, body.reason)
        return {
            "ok": True,
            "id": req.id,
            "status": req.status,
            "decision_reason": req.decision_reason,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


# --- Task Verification Endpoints ---

@app.get("/api/hr/tasks/verification-queue")
def hr_verification_queue(
    user: User = Depends(require_role("hr")),
    db: Session = Depends(get_db),
):
    return get_tasks_for_verification_hr(db)


@app.post("/api/hr/tasks/{task_id}/verify")
def hr_verify_task_endpoint(
    task_id: str,
    body: TaskVerifyIn,
    user: User = Depends(require_role("hr")),
    db: Session = Depends(get_db),
):
    try:
        numeric_id = int(task_id.removeprefix("T-"))
    except ValueError:
        raise HTTPException(400, "Invalid task id")
    try:
        task = hr_verify_task(db, numeric_id, user, body.notes)
        return {
            "ok": True,
            "id": task_id,
            "verification_status": task.verification_status,
            "verified_by_id": task.verified_by_id,
            "verified_at": task.verified_at.isoformat() if task.verified_at else None,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/hr/tasks/{task_id}/request-changes")
def hr_request_changes_endpoint(
    task_id: str,
    body: TaskRequestChangesIn,
    user: User = Depends(require_role("hr")),
    db: Session = Depends(get_db),
):
    try:
        numeric_id = int(task_id.removeprefix("T-"))
    except ValueError:
        raise HTTPException(400, "Invalid task id")
    try:
        task = hr_request_task_changes(db, numeric_id, user, body.notes)
        return {
            "ok": True,
            "id": task_id,
            "status": task.status,
            "progress": task.completion_percentage,
            "verification_status": task.verification_status,
            "verification_notes": task.verification_notes,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


# ===============================================================
# MANAGER DASHBOARD & TEAM APIS
# ===============================================================

@app.get("/api/manager/dashboard")
def mgr_dash(user: User = Depends(require_role("manager", "hr")), db: Session = Depends(get_db)):
    if user.role == "hr":
        team_members = db.query(User).filter(User.role == "employee").all()
    else:
        team_members = (
            db.query(User)
            .filter(
                or_(
                    User.manager_name == user.name,
                    User.manager_id == user.id,
                )
            )
            .all()
        )
        if not team_members:
            team_members = db.query(User).filter(User.department == user.department, User.role == "employee").all()

    member_ids = [m.id for m in team_members]
    latest_pred = {}
    if member_ids:
        preds = (
            db.query(Prediction)
            .distinct(Prediction.employee_id)
            .filter(Prediction.employee_id.in_(member_ids))
            .order_by(Prediction.employee_id, Prediction.id.desc())
            .all()
        )
        latest_pred = {p.employee_id: p for p in preds}

    members_data = []
    high_count = 0
    mod_count = 0
    low_count = 0
    warnings = []

    u_core = get_employees_core_metrics_batch(db, team_members)
    for m in team_members:
        core = u_core.get(m.id) or get_employee_core_metrics(db, m)
        score = core["burnout_score"] if core["burnout_score"] is not None else 50
        status_str = core["risk_level"].title() if core["risk_level"] else "Moderate"

        if status_str == "High" or score >= 70:
            high_count += 1
            status_str = "High"
        elif status_str == "Low" or score < 40:
            low_count += 1
            status_str = "Low"
        else:
            mod_count += 1
            status_str = "Moderate"

        factors_list = [f.get("name", "") for f in (core.get("risk_factors") or [])[:3]]

        members_data.append({
            "id": m.employee_code or f"E{m.id}",
            "raw_id": m.id,
            "user_id": m.id,
            "name": m.name,
            "role": m.department or "Engineer",
            "workload": core["workload_score"] if core["workload_score"] is not None else 50,
            "stress": core["stress_score"] if core["stress_score"] is not None else 50,
            "burnout": score,
            "hours": core["working_hours_num"] if core["working_hours_num"] is not None else 8.5,
            "status": status_str,
            "dept": m.department or "Engineering",
        })

        if status_str == "High":
            warnings.append({
                "id": m.employee_code or f"E{m.id}",
                "name": m.name,
                "current": score,
                "previous": max(30, score - 15),
                "change": 15,
                "factors": factors_list or ["Workload ↑", "Stress ↑"],
            })

    total = len(team_members)
    dist = [
        {"name": "High", "value": high_count, "fill": "#ef4444"},
        {"name": "Moderate", "value": mod_count, "fill": "#f59e0b"},
        {"name": "Low", "value": low_count, "fill": "#22c55e"},
    ]

    # Real team historical trends for 7 days
    today = date.today()
    days_7 = [today - timedelta(days=i) for i in range(6, -1, -1)]

    # Real team attendance aggregated by date
    team_att = db.query(Attendance).filter(
        Attendance.employee_id.in_(member_ids),
        Attendance.date >= days_7[0],
        Attendance.date <= days_7[-1]
    ).all() if member_ids else []
    att_by_date = {}
    for a in team_att:
        att_by_date.setdefault(a.date, []).append(a)

    hours_week = []
    for d in days_7:
        day_atts = att_by_date.get(d, [])
        valid = [a for a in day_atts if a.working_minutes]
        if valid:
            avg_h = round(sum(a.working_minutes for a in valid) / len(valid) / 60, 1)
            avg_ot = round(sum((a.overtime_minutes or 0) for a in valid) / len(valid) / 60, 1)
        else:
            avg_h, avg_ot = 0.0, 0.0
        hours_week.append({"day": d.strftime("%a"), "hours": avg_h, "ot": avg_ot})

    # Real team predictions aggregated by date
    team_preds = db.query(Prediction).filter(
        Prediction.employee_id.in_(member_ids),
        Prediction.prediction_date >= datetime.combine(days_7[0], time.min)
    ).all() if member_ids else []
    preds_by_date = {}
    for p in team_preds:
        p_d = p.prediction_date.date() if isinstance(p.prediction_date, datetime) else p.prediction_date
        if p_d and p.burnout_score is not None:
            preds_by_date.setdefault(p_d, []).append(p.burnout_score)

    burnout_trend_7 = []
    for d in days_7:
        p_scores = preds_by_date.get(d, [])
        if p_scores:
            b_val = round(sum(p_scores) / len(p_scores))
        else:
            b_val = round(sum(m["burnout"] for m in members_data) / max(len(members_data), 1))
        burnout_trend_7.append({"day": d.strftime("%a"), "value": b_val})

    # Real team surveys aggregated by date
    team_surveys = db.query(Survey).filter(
        Survey.employee_id.in_(member_ids),
        Survey.date >= days_7[0],
        Survey.date <= days_7[-1]
    ).all() if member_ids else []
    surveys_by_date = {}
    for s in team_surveys:
        surveys_by_date.setdefault(s.date, []).append(s)

    stress_trend_7 = []
    for d in days_7:
        day_surveys = surveys_by_date.get(d, [])
        if day_surveys:
            st_scores = []
            wl_scores = []
            for s in day_surveys:
                ans = s.answers or {}
                st = ans.get("stress")
                wl = ans.get("workload", ans.get("manageable"))
                if st is not None:
                    try:
                        st_scores.append(float(st) * 20.0)
                    except Exception:
                        pass
                if wl is not None:
                    try:
                        wl_scores.append(float(wl) * 20.0)
                    except Exception:
                        pass
            avg_st = round(sum(st_scores) / len(st_scores)) if st_scores else round(sum(m["stress"] for m in members_data) / max(len(members_data), 1))
            avg_wl = round(sum(wl_scores) / len(wl_scores)) if wl_scores else round(sum(m["workload"] for m in members_data) / max(len(members_data), 1))
        else:
            avg_st = round(sum(m["stress"] for m in members_data) / max(len(members_data), 1))
            avg_wl = round(sum(m["workload"] for m in members_data) / max(len(members_data), 1))
        stress_trend_7.append({"day": d.strftime("%a"), "stress": avg_st, "workload": avg_wl})

    avg_team_wl = round(sum(m["workload"] for m in members_data) / max(len(members_data), 1))
    avg_team_st = round(sum(m["stress"] for m in members_data) / max(len(members_data), 1))
    ea_today = [
        {"metric": "Workload", "expected": 3, "actual": max(1, min(5, avg_team_wl // 20))},
        {"metric": "Stress", "expected": 2, "actual": max(1, min(5, avg_team_st // 20))},
        {"metric": "Difficulty", "expected": 3, "actual": 3},
    ]

    # Fetch or generate manager's own burnout prediction
    my_pred = db.query(Prediction).filter(Prediction.employee_id == user.id).order_by(Prediction.id.desc()).first()
    if not my_pred:
        try:
            p_gen = predict_for_employee(db, user, persist=True)
            if not p_gen.get("insufficient_data"):
                my_pred = db.query(Prediction).filter(Prediction.employee_id == user.id).order_by(Prediction.id.desc()).first()
        except Exception:
            pass

    my_burnout = None
    if my_pred:
        b_score = int(round(my_pred.burnout_score)) if my_pred.burnout_score is not None else None
        factors = [
            {"name": f.get("feature", f.get("name", "")).replace("_", " ").title(), "impact": f.get("importance", 0)}
            for f in (my_pred.top_factors or [])
        ]
        recs_list = my_pred.recommendations or []
        if not recs_list and my_pred.top_factors:
            from .services.recommendation_service import recommendations_from_factors
            recs_list = recommendations_from_factors(my_pred.top_factors, my_pred.risk_level or "LOW")
        my_burnout = {
            "has_prediction": True,
            "burnout_score": b_score,
            "risk_level": my_pred.risk_level or ("HIGH" if (b_score or 0) >= 70 else ("MODERATE" if (b_score or 0) >= 40 else "LOW")),
            "confidence": my_pred.confidence,
            "risk_factors": factors,
            "recommendations": recs_list,
            "explanation": getattr(my_pred, "explanation", None) or (recs_list[0] if recs_list else ""),
        }
    else:
        my_burnout = {
            "has_prediction": False,
            "burnout_score": None,
            "risk_level": "Unavailable",
            "risk_factors": [],
            "recommendations": [],
            "explanation": "No burnout prediction recorded yet for this manager.",
        }

    return {
        "manager": {"id": user.id, "name": user.name, "email": user.email, "department": user.department},
        "members": members_data,
        "dist": dist,
        "totalMembers": total,
        "highRisk": high_count,
        "modRisk": mod_count,
        "lowRisk": low_count,
        "warnings": warnings,
        "my_burnout": my_burnout,
        "kpis": _kpis_for(user, db),
        "burnoutTrend7": burnout_trend_7,
        "burnout_trend": burnout_trend_7,
        "hoursWeek": hours_week,
        "hours_trend": hours_week,
        "stressTrend": stress_trend_7,
        "stress_trend": stress_trend_7,
        "expectedActualToday": ea_today,
    }


@app.get("/api/manager/team")
def mgr_team(user: User = Depends(require_role("manager", "hr")), db: Session = Depends(get_db)):
    dash = mgr_dash(user, db)
    return dash["members"]


@app.get("/api/users/{user_id}/details")
@app.get("/api/employee/{user_id}/full-details")
@app.get("/api/manager/team/{user_id}/details")
def get_user_full_details(
    user_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    clean_id = str(user_id).strip()
    target = None

    if clean_id.isdigit():
        target = db.query(User).filter(User.id == int(clean_id)).first()

    if not target:
        target = db.query(User).filter(func.lower(User.employee_code) == clean_id.lower()).first()

    if not target:
        target = db.query(User).filter(func.lower(User.email) == clean_id.lower()).first()

    if not target:
        target = db.query(User).filter(func.lower(User.name) == clean_id.lower()).first()

    if not target:
        raise HTTPException(404, f"Employee with ID '{user_id}' not found.")

    # Strict RBAC access control
    if user.role == "hr":
        pass  # HR has organization-wide access
    elif user.role == "manager":
        is_self = (target.id == user.id)
        is_direct_report = (target.manager_id == user.id or target.manager_name == user.name)
        is_same_dept = (target.department == user.department)
        if not (is_self or is_direct_report or is_same_dept):
            raise HTTPException(403, "Access forbidden: You can only view details of employees within your authorized team.")
    else:  # Employee
        if target.id != user.id:
            raise HTTPException(403, "Access forbidden: You cannot view other employees' private records.")

    # 1. Profile details
    profile = {
        "id": target.id,
        "employee_id": target.employee_code or f"E{target.id}",
        "name": target.name,
        "email": target.email,
        "role": target.role.title() if target.role else "Employee",
        "department": target.department or "Engineering",
        "manager": target.manager_name or "—",
        "phone": target.phone or "+91 98765 43210",
        "avatar": target.avatar or None,
        "account_status": "Active",
    }

    # 2. Attendance history (records for this exact user)
    atts = db.query(Attendance).filter(Attendance.employee_id == target.id).order_by(Attendance.date.desc()).all()
    attendance_list = []
    for a in atts:
        h = a.working_minutes // 60 if a.working_minutes else 0
        m = a.working_minutes % 60 if a.working_minutes else 0
        ot_h = a.overtime_minutes // 60 if a.overtime_minutes else 0
        ot_m = a.overtime_minutes % 60 if a.overtime_minutes else 0

        status_text = "Present" if a.check_in else "Absent"
        if a.final_status:
            status_text = a.final_status.title()

        exceptions = []
        if a.late_minutes and a.late_minutes > 0:
            exceptions.append(f"Late by {a.late_minutes}m")
        if a.early_checkout_minutes and a.early_checkout_minutes > 0:
            exceptions.append(f"Early checkout ({a.early_checkout_minutes}m)")

        attendance_list.append({
            "date": a.date.strftime("%d %b %Y"),
            "check_in": a.check_in or "—",
            "check_out": a.check_out or "—",
            "working_hours": f"{h}h {m}m" if a.working_minutes else "—",
            "overtime": f"{ot_h}h {ot_m}m" if a.overtime_minutes else "0m",
            "status": status_text,
            "exceptions": ", ".join(exceptions) if exceptions else "None",
        })

    # 3. Tasks and work progress (strictly assigned to this user)
    tasks = db.query(Task).filter(Task.employee_id == target.id).order_by(Task.id.desc()).all()
    task_list = []
    for t in tasks:
        task_list.append({
            "id": f"T-{t.id}",
            "title": t.name or "Untitled Task",
            "description": t.description or "",
            "priority": t.priority or "Medium",
            "status": t.status or "Pending",
            "progress": t.completion_percentage if t.completion_percentage is not None else 0,
            "deadline": t.deadline or (t.due_date.strftime("%d %b %Y") if t.due_date else "—"),
            "start_date": t.start_date.strftime("%d %b %Y") if t.start_date else None,
            "due_date": t.due_date.strftime("%d %b %Y") if t.due_date else None,
            "blockers": t.blocked_reason or "",
            "work_update": t.work_update or "",
        })

    # 4. Leave & permission history
    leaves = db.query(LeaveRequest).filter(LeaveRequest.employee_id == target.id).order_by(LeaveRequest.id.desc()).all()
    leave_list = []
    for l in leaves:
        d_str = l.date
        if l.start_date and l.end_date:
            d_str = f"{l.start_date.strftime('%d %b')} – {l.end_date.strftime('%d %b %Y')}"
        leave_list.append({
            "id": f"LR-{l.id}",
            "type": l.leave_type or l.type or "Leave",
            "dates": d_str,
            "duration": l.duration or "1 day",
            "status": l.status,
            "reason": l.reason or "—",
            "session": l.half_day_session,
        })

    perms = db.query(PermissionRequest).filter(PermissionRequest.employee_id == target.id).order_by(PermissionRequest.id.desc()).all()
    permission_list = []
    for p in perms:
        permission_list.append({
            "id": f"PR-{p.id}",
            "date": p.date.strftime("%d %b %Y") if p.date else "—",
            "requested_checkout_time": p.requested_checkout_time,
            "status": p.status,
            "reason": p.reason or "—",
        })

    # 5. Authoritative Core Metrics from Central Service
    core = get_employee_core_metrics(db, target)

    wellbeing = {
        "has_prediction": core["has_prediction"],
        "burnout_score": core["burnout_score"],
        "risk_level": core["risk_level"],
        "prediction_timestamp": core["prediction_timestamp"],
        "workload_score": core["workload_score"],
        "work_life_balance_score": core["wlb_score"],
        "working_hours": core["working_hours_display"],
        "working_hours_num": core["working_hours_num"],
        "risk_factors": core["risk_factors"],
        "recommendations": core["recommendations"],
        "explanation": core["explanation"],
    }

    workload = {
        "total_tasks": core["total_tasks"],
        "active_tasks": core["active_tasks"],
        "completed_tasks": core["completed_tasks"],
        "completion_rate": core["completion_rate"],
        "blocked_tasks": core["blocked_tasks"],
        "workload_score": core["workload_score"],
        "work_life_balance_score": core["wlb_score"],
        "working_hours": core["working_hours_display"],
        "working_hours_num": core["working_hours_num"],
    }

    # Distinct team-level metrics for managers
    team_stats = None
    if target.role == "manager":
        team_tasks = db.query(Task).filter(Task.assigned_by_id == target.id).all()
        team_members = db.query(User).filter(or_(User.manager_id == target.id, User.manager_name == target.name)).all()
        team_stats = {
            "team_members_count": len(team_members),
            "team_tasks_count": len(team_tasks),
            "team_tasks_active": sum(1 for t in team_tasks if t.status not in ("Completed", "Done")),
            "team_tasks_completed": sum(1 for t in team_tasks if t.status in ("Completed", "Done")),
        }

    return {
        "profile": profile,
        "attendance": attendance_list,
        "tasks": task_list,
        "leaves": leave_list,
        "permissions": permission_list,
        "workload": workload,
        "wellbeing": wellbeing,
        "team_stats": team_stats,
    }



@app.get("/api/manager/trends")
def mgr_trends(
    days: int = Query(7),
    user: User = Depends(require_role("manager", "hr")),
    db: Session = Depends(get_db)
):
    if user.role == "hr":
        team_members = db.query(User).filter(User.role.in_(["employee", "manager"])).all()
    else:
        team_members = db.query(User).filter(
            or_(
                User.manager_name == user.name,
                User.manager_id == user.id,
                User.department == user.department,
            ),
            User.role == "employee",
        ).all()
    member_ids = [m.id for m in team_members]

    today = date.today()
    date_list = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]

    # Real team attendance aggregated by date
    team_att = db.query(Attendance).filter(
        Attendance.employee_id.in_(member_ids),
        Attendance.date >= date_list[0],
        Attendance.date <= date_list[-1]
    ).all() if member_ids else []
    att_by_date = {}
    for a in team_att:
        att_by_date.setdefault(a.date, []).append(a)

    hours_trend = []
    overtime_trend = []
    for d in date_list:
        label = d.strftime("%d %b") if days > 7 else d.strftime("%a")
        day_atts = att_by_date.get(d, [])
        valid = [a for a in day_atts if a.working_minutes]
        if valid:
            avg_h = round(sum(a.working_minutes for a in valid) / len(valid) / 60, 1)
            avg_ot = round(sum((a.overtime_minutes or 0) for a in valid) / len(valid) / 60, 1)
        else:
            avg_h, avg_ot = 0.0, 0.0
        hours_trend.append({"day": label, "hours": avg_h, "ot": avg_ot})
        overtime_trend.append({"day": label, "hours": avg_h, "ot": avg_ot})

    # Real team predictions aggregated by date
    team_preds = db.query(Prediction).filter(
        Prediction.employee_id.in_(member_ids),
        Prediction.prediction_date >= datetime.combine(date_list[0], time.min)
    ).all() if member_ids else []
    preds_by_date = {}
    for p in team_preds:
        p_d = p.prediction_date.date() if isinstance(p.prediction_date, datetime) else p.prediction_date
        if p_d and p.burnout_score is not None:
            preds_by_date.setdefault(p_d, []).append(p.burnout_score)

    dash = mgr_dash(user, db)
    members = dash["members"]
    avg_burnout = int(sum(m["burnout"] for m in members) / max(len(members), 1))
    avg_stress = int(sum(m["stress"] for m in members) / max(len(members), 1))
    avg_workload = int(sum(m["workload"] for m in members) / max(len(members), 1))

    burnout_trend = []
    for d in date_list:
        label = d.strftime("%d %b") if days > 7 else d.strftime("%a")
        p_scores = preds_by_date.get(d, [])
        if p_scores:
            b_val = round(sum(p_scores) / len(p_scores))
        else:
            b_val = avg_burnout
        burnout_trend.append({"day": label, "value": b_val})

    # Real team surveys aggregated by date
    team_surveys = db.query(Survey).filter(
        Survey.employee_id.in_(member_ids),
        Survey.date >= date_list[0],
        Survey.date <= date_list[-1]
    ).all() if member_ids else []
    surveys_by_date = {}
    for s in team_surveys:
        surveys_by_date.setdefault(s.date, []).append(s)

    stress_trend = []
    for d in date_list:
        label = d.strftime("%d %b") if days > 7 else d.strftime("%a")
        day_surveys = surveys_by_date.get(d, [])
        if day_surveys:
            st_scores = []
            wl_scores = []
            for s in day_surveys:
                ans = s.answers or {}
                st = ans.get("stress")
                wl = ans.get("workload", ans.get("manageable"))
                if st is not None:
                    try:
                        st_scores.append(float(st) * 20.0)
                    except Exception:
                        pass
                if wl is not None:
                    try:
                        wl_scores.append(float(wl) * 20.0)
                    except Exception:
                        pass
            avg_st = round(sum(st_scores) / len(st_scores)) if st_scores else avg_stress
            avg_wl = round(sum(wl_scores) / len(wl_scores)) if wl_scores else avg_workload
        else:
            avg_st, avg_wl = avg_stress, avg_workload
        stress_trend.append({"day": label, "stress": avg_st, "workload": avg_wl})

    return {
        "burnoutTrend7": burnout_trend,
        "burnout_trend": burnout_trend,
        "stressTrend": stress_trend,
        "stress_trend": stress_trend,
        "hoursWeek": hours_trend,
        "hours_trend": hours_trend,
        "overtime_trend": overtime_trend,
        "avgBurnout": avg_burnout,
        "avgStress": avg_stress,
        "avgWorkload": avg_workload,
        "expectedActualToday": [
            {"metric": "Workload", "expected": 3, "actual": max(1, min(5, avg_workload // 20))},
            {"metric": "Stress", "expected": 2, "actual": max(1, min(5, avg_stress // 20))},
            {"metric": "Difficulty", "expected": 3, "actual": 3},
        ],
        "communicationSentiment": [
            {"week": "W1", "positive": 65, "neutral": 25, "negative": 10},
            {"week": "W2", "positive": 60, "neutral": 28, "negative": 12},
            {"week": "W3", "positive": 57, "neutral": 29, "negative": 14},
            {"week": "W4", "positive": 55, "neutral": 30, "negative": 15},
        ],
    }


# ===============================================================
# HR DASHBOARD & ANALYTICS APIS
# ===============================================================

def calculate_department_stats(db: Session, users: list[User], u_core: dict[int, dict]) -> list[dict]:
    dept_records = db.query(Department).all()
    dept_names = [d.name for d in dept_records]
    user_depts = [u.department for u in users if u.department]
    all_depts = list(dict.fromkeys(dept_names + user_depts))

    dept_stats = []
    for d in all_depts:
        dept_users = [u for u in users if u.department == d]
        if not dept_users:
            continue
        scores = [u_core[u.id]["burnout_score"] for u in dept_users if u.id in u_core and u_core[u.id]["burnout_score"] is not None]
        wl_scores = [u_core[u.id]["workload_score"] for u in dept_users if u.id in u_core and u_core[u.id]["workload_score"] is not None]
        st_scores = [u_core[u.id]["stress_score"] for u in dept_users if u.id in u_core and u_core[u.id]["stress_score"] is not None]
        ot_scores = [u_core[u.id]["overtime_hours_num"] for u in dept_users if u.id in u_core and u_core[u.id]["overtime_hours_num"] is not None]

        avg_s = int(round(sum(scores) / len(scores))) if scores else 50
        avg_wl = int(round(sum(wl_scores) / len(wl_scores))) if wl_scores else 50
        avg_st = int(round(sum(st_scores) / len(st_scores))) if st_scores else 50
        avg_ot = round(sum(ot_scores) / len(ot_scores), 1) if ot_scores else 0.0

        dept_stats.append({
            "name": d,
            "risk": avg_s,
            "workload": avg_wl,
            "stress": avg_st,
            "overtime": avg_ot,
        })
    return dept_stats


def calculate_hr_trends(db: Session, users: list[User], u_core: dict[int, dict]) -> list[dict]:
    today = date.today()
    month_ranges = []
    for m_offset in range(5, -1, -1):
        year = today.year
        month = today.month - m_offset
        while month <= 0:
            month += 12
            year -= 1
        m_start = date(year, month, 1)
        if month == 12:
            m_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            m_end = date(year, month + 1, 1) - timedelta(days=1)
        month_ranges.append((m_start, m_end, m_start.strftime("%b")))

    overall_start = month_ranges[0][0]
    overall_end = month_ranges[-1][1]

    # Bulk fetch 6-month historical dataset in 3 bounded queries instead of 18 sequential round-trips
    all_preds = db.query(Prediction).filter(
        Prediction.prediction_date >= datetime.combine(overall_start, time.min),
        Prediction.prediction_date <= datetime.combine(overall_end, time.max)
    ).all()

    all_atts = db.query(Attendance).filter(
        Attendance.date >= overall_start,
        Attendance.date <= overall_end
    ).all()

    all_surveys = db.query(Survey).filter(
        Survey.date >= overall_start,
        Survey.date <= overall_end
    ).all()

    valid_cores_b = [u_core[u.id]["burnout_score"] for u in users if u.id in u_core and u_core[u.id]["burnout_score"] is not None]
    valid_cores_st = [u_core[u.id]["stress_score"] for u in users if u.id in u_core and u_core[u.id]["stress_score"] is not None]
    valid_cores_wl = [u_core[u.id]["workload_score"] for u in users if u.id in u_core and u_core[u.id]["workload_score"] is not None]

    default_b = round(sum(valid_cores_b) / len(valid_cores_b)) if valid_cores_b else 50
    default_st = round(sum(valid_cores_st) / len(valid_cores_st)) if valid_cores_st else 50
    default_wl = round(sum(valid_cores_wl) / len(valid_cores_wl)) if valid_cores_wl else 50

    trend = []
    for m_start, m_end, m_label in month_ranges:
        start_dt = datetime.combine(m_start, time.min)
        end_dt = datetime.combine(m_end, time.max)

        valid_b = [p.burnout_score for p in all_preds if p.prediction_date and start_dt <= p.prediction_date <= end_dt and p.burnout_score is not None]
        avg_b = round(sum(valid_b) / len(valid_b)) if valid_b else default_b

        m_atts = [a for a in all_atts if a.date and m_start <= a.date <= m_end]
        ot_hours = round(sum((a.overtime_minutes or 0) for a in m_atts) / max(len(m_atts), 1) / 60, 1) if m_atts else 0.0

        m_surveys = [s for s in all_surveys if s.date and m_start <= s.date <= m_end]
        st_list = []
        wl_list = []
        for s in m_surveys:
            ans = s.answers or {}
            st = ans.get("stress")
            wl = ans.get("workload", ans.get("manageable"))
            if st is not None:
                try:
                    st_list.append(float(st) * 20.0)
                except Exception:
                    pass
            if wl is not None:
                try:
                    wl_list.append(float(wl) * 20.0)
                except Exception:
                    pass
        avg_st = round(sum(st_list) / len(st_list)) if st_list else default_st
        avg_wl = round(sum(wl_list) / len(wl_list)) if wl_list else default_wl

        trend.append({
            "month": m_label,
            "burnout": avg_b,
            "stress": avg_st,
            "workload": avg_wl,
            "overtime": ot_hours,
        })
    return trend


@app.get("/api/hr/dashboard")
def hr_dash(user: User = Depends(require_role("hr")), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.role.in_(["employee", "manager"])).all()

    # Calculate authoritative core metrics in batch (5 bulk queries total)
    u_core = get_employees_core_metrics_batch(db, users)

    high_count = 0
    mod_count = 0
    low_count = 0

    for u in users:
        core = u_core.get(u.id)
        s = core["burnout_score"] if (core and core["burnout_score"] is not None) else 50
        if s >= 70:
            high_count += 1
        elif s < 40:
            low_count += 1
        else:
            mod_count += 1

    dept_stats = calculate_department_stats(db, users, u_core)

    total = len(users)
    dist = [
        {"name": "High", "value": high_count, "fill": "#ef4444"},
        {"name": "Moderate", "value": mod_count, "fill": "#f59e0b"},
        {"name": "Low", "value": low_count, "fill": "#22c55e"},
    ]

    trend = calculate_hr_trends(db, users, u_core)

    return {
        "hr": {"name": user.name},
        "totalEmployees": total,
        "highRisk": high_count,
        "modRisk": mod_count,
        "lowRisk": low_count,
        "dist": dist,
        "departments": dept_stats,
        "trend": trend,
    }


@app.get("/api/hr/trends")
def hr_trends(user: User = Depends(require_role("hr")), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.role.in_(["employee", "manager"])).all()
    u_core = get_employees_core_metrics_batch(db, users)
    trend = calculate_hr_trends(db, users, u_core)
    dept_stats = calculate_department_stats(db, users, u_core)

    high_count = sum(1 for u in users if (u_core.get(u.id) or {}).get("burnout_score", 50) >= 70)
    low_count = sum(1 for u in users if (u_core.get(u.id) or {}).get("burnout_score", 50) < 40)
    mod_count = len(users) - high_count - low_count

    dist = [
        {"name": "High", "value": high_count, "fill": "#ef4444"},
        {"name": "Moderate", "value": mod_count, "fill": "#f59e0b"},
        {"name": "Low", "value": low_count, "fill": "#22c55e"},
    ]

    return {
        "trend": trend,
        "trends": trend,
        "departments": dept_stats,
        "totalEmployees": len(users),
        "dist": dist,
    }


@app.get("/api/hr/employees")
def hr_emp(user: User = Depends(require_role("hr")), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.role.in_(["employee", "manager"])).all()
    today = date.today()

    today_atts = db.query(Attendance).filter(Attendance.date == today).all()
    att_by_user = {a.employee_id: a for a in today_atts}

    u_core = get_employees_core_metrics_batch(db, users)

    out = []
    for u in users:
        core = u_core.get(u.id) or {}
        att = att_by_user.get(u.id)
        out.append({
            "id": u.employee_code or f"E{u.id}",
            "raw_id": u.id,
            "user_id": u.id,
            "name": u.name,
            "dept": u.department or "Engineering",
            "role": u.role.title() if u.role else "Employee",
            "status": "Active",
            "burnout": core.get("burnout_score") if core.get("burnout_score") is not None else 50,
            "workload": core.get("workload_score") if core.get("workload_score") is not None else 50,
            "lastCheckIn": att.check_in if (att and att.check_in) else "—",
        })
    return out


@app.get("/api/hr/departments")
def hr_dept(user: User = Depends(require_role("hr")), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.role.in_(["employee", "manager"])).all()
    u_core = get_employees_core_metrics_batch(db, users)
    return calculate_department_stats(db, users, u_core)


@app.get("/api/hr/model-performance")
def model_perf(user: User = Depends(require_role("hr"))):
    meta = load_metadata()
    models_list = []
    comp = meta.get("comparison", {})
    for name, metrics in comp.items():
        models_list.append({
            "name": name,
            "accuracy": metrics.get("accuracy", 0.0),
            "precision": metrics.get("precision_macro", 0.0),
            "recall": metrics.get("recall_macro", 0.0),
            "f1": metrics.get("f1_macro", 0.0),
        })
    features = [
        {"name": f["name"].replace("_", " ").title(), "importance": round(f["importance"], 4)}
        for f in meta.get("feature_importances", meta.get("features", []))
    ]
    test_metrics = meta.get("test_metrics", {})
    return {
        "disclaimer": meta.get("disclaimer", "Academic / Prototype Model. Not a medical diagnosis."),
        "model_version": meta.get("model_version", "burnout_rf_v1.0"),
        "dataset_size": meta.get("dataset_size", "2,400 observations"),
        "recall_high": test_metrics.get("recall_high", 0.82),
        "semantic_backend": meta.get("semantic_backend", "TF-IDF + SVD"),
        "models": models_list,
        "features": features,
        "confusion": test_metrics.get("confusion_matrix", [[45, 5], [4, 46]]),
    }


@app.get("/api/hr/interventions")
def get_hr_interventions(user: User = Depends(require_role("hr")), db: Session = Depends(get_db)):
    all_users = db.query(User).all()
    user_map = {u.id: u for u in all_users}
    interventions = db.query(Intervention).order_by(Intervention.id.desc()).all()
    res = []
    for it in interventions:
        emp = user_map.get(it.employee_id)
        action_list = [a.strip() for a in (it.notes or it.recommendation or it.trigger_reason or "Assessment recorded").split(";") if a.strip()]
        timeline = [
            {"date": it.created_at.strftime("%d %b") if it.created_at else "Today", "event": f"Initiated: {it.trigger_reason or it.intervention_type}"}
        ]
        if it.notes and it.status != "OPEN":
            timeline.append({"date": it.updated_at.strftime("%d %b") if it.updated_at else "Today", "event": f"Status: {it.status} - {it.notes}"})
        if it.status == "RESOLVED" and it.resolution:
            timeline.append({"date": it.updated_at.strftime("%d %b") if it.updated_at else "Today", "event": f"Resolved: {it.resolution}"})

        res.append({
            "id": f"INT-{it.id}",
            "raw_id": it.id,
            "employee_id": emp.employee_code if emp else f"E{it.employee_id}",
            "employee": it.employee_name or (emp.name if emp else f"User {it.employee_id}"),
            "empId": emp.employee_code if emp else f"E{it.employee_id}",
            "department": emp.department if emp else "Engineering",
            "created_by": it.created_by or "HR Team",
            "risk_level": it.risk_level or "High",
            "trigger_reason": it.trigger_reason or "",
            "intervention_type": it.intervention_type or "Workload Review",
            "recommendation": it.recommendation or "",
            "status": (it.status or "OPEN").upper(),
            "notes": it.notes or "",
            "resolution": it.resolution or "",
            "follow_up_date": it.follow_up_date.strftime("%Y-%m-%d") if it.follow_up_date else "",
            "created_at": it.created_at.strftime("%d %b %Y") if it.created_at else "",
            "updated_at": it.updated_at.strftime("%d %b %Y, %I:%M %p") if it.updated_at else "",
            "actions": action_list or ["Assessment recorded"],
            "timeline": timeline,
        })
    return res


@app.get("/api/hr/interventions/candidates")
def get_intervention_candidates(user: User = Depends(require_role("hr")), db: Session = Depends(get_db)):
    from sqlalchemy import func
    users = db.query(User).filter(User.role.in_(["employee", "manager"])).all()

    all_preds = db.query(Prediction).order_by(Prediction.employee_id, Prediction.id.desc()).all()
    latest_pred = {}
    for p in all_preds:
        if p.employee_id not in latest_pred:
            latest_pred[p.employee_id] = p

    blocked_counts = dict(
        db.query(Task.employee_id, func.count(Task.id))
        .filter(Task.status == "Blocked")
        .group_by(Task.employee_id)
        .all()
    )

    candidates = []
    for u in users:
        pred = latest_pred.get(u.id)
        blocked_count = blocked_counts.get(u.id, 0)
        score = pred.burnout_score if (pred and pred.burnout_score is not None) else 50
        level = pred.risk_level if (pred and pred.risk_level) else "MODERATE"
        reason_parts = []
        if level == "HIGH" or score >= 70:
            reason_parts.append(f"High Burnout Risk ({round(score)})")
        if blocked_count > 0:
            reason_parts.append(f"{blocked_count} Blocked Task(s)")
        if not reason_parts and score >= 55:
            reason_parts.append(f"Elevated workload stress ({round(score)})")

        candidates.append({
            "id": u.id,
            "employee_id": u.employee_code or f"E{u.id}",
            "name": u.name,
            "role": u.role,
            "department": u.department,
            "risk_score": round(score),
            "risk_level": level,
            "reason": " & ".join(reason_parts) if reason_parts else "Routine wellbeing check",
            "suggested_type": "Workload Review" if blocked_count > 0 else "1-on-1 Wellbeing Sync",
        })
    return candidates


@app.post("/api/hr/interventions")
def create_hr_intervention(body: InterventionIn, user: User = Depends(require_role("hr")), db: Session = Depends(get_db)):
    target_id = None
    raw_target = body.employee_id
    if isinstance(raw_target, str) and (raw_target.startswith("E") or raw_target.startswith("M") or raw_target.startswith("H")):
        target_user = db.query(User).filter(User.employee_code == raw_target).first()
        if target_user:
            target_id = target_user.id
    else:
        try:
            target_id = int(str(raw_target).removeprefix("E").removeprefix("M"))
        except ValueError:
            pass

    emp = db.query(User).filter(User.id == target_id).first() if target_id else None
    if not emp:
        raise HTTPException(404, "Target employee not found")

    fu_date = None
    if body.follow_up_date:
        try:
            fu_date = datetime.strptime(body.follow_up_date, "%Y-%m-%d").date()
        except ValueError:
            pass

    status_val = (body.status or "OPEN").upper()
    if status_val not in ("OPEN", "IN_PROGRESS", "RESOLVED"):
        status_val = "OPEN"

    it = Intervention(
        employee_id=emp.id,
        employee_name=emp.name,
        created_by_id=user.id,
        created_by=user.name,
        risk_level=body.risk_level or "High",
        trigger_reason=body.trigger_reason or "Workload / burnout indicators detected",
        intervention_type=body.intervention_type or "Workload Review",
        recommendation=body.recommendation or "1-on-1 check-in and workload re-balancing",
        status=status_val,
        follow_up_date=fu_date,
        notes=body.notes or "",
        resolution=body.resolution or "",
        created_at=datetime.utcnow(),
    )
    db.add(it)
    db.commit()
    db.refresh(it)

    log_audit(
        db,
        actor=user,
        action="INTERVENTION_CREATED",
        target_type="intervention",
        target_id=it.id,
        new_value={"employee": emp.name, "type": it.intervention_type, "status": it.status},
    )

    # Phase 3.J: Notify Employee of wellbeing support plan (excluding confidential notes)
    create_notification(
        db,
        recipient_id=emp.id,
        title="Wellbeing Support Plan",
        body=f"A support action '{it.recommendation[:70]}' has been initiated to support your workplace wellbeing.",
        notification_type="WELLBEING_INTERVENTION",
        entity_type="intervention",
        entity_id=it.id,
        priority="normal",
        link_url="/employee/recommendations",
        dedup_key=f"intervention_{it.id}",
    )

    return {
        "ok": True,
        "id": f"INT-{it.id}",
        "raw_id": it.id,
        "employee": emp.name,
        "empId": emp.employee_code,
        "department": emp.department,
        "status": it.status,
        "risk_level": it.risk_level,
        "intervention_type": it.intervention_type,
        "trigger_reason": it.trigger_reason,
        "recommendation": it.recommendation,
        "notes": it.notes,
        "follow_up_date": it.follow_up_date.strftime("%Y-%m-%d") if it.follow_up_date else "",
        "created_at": it.created_at.strftime("%d %b %Y"),
    }


@app.patch("/api/hr/interventions/{intervention_id}")
def update_hr_intervention(intervention_id: str, body: InterventionUpdateIn, user: User = Depends(require_role("hr")), db: Session = Depends(get_db)):
    try:
        numeric_id = int(intervention_id.removeprefix("INT-"))
    except ValueError:
        raise HTTPException(400, "Invalid intervention ID")

    it = db.query(Intervention).filter(Intervention.id == numeric_id).first()
    if not it:
        raise HTTPException(404, "Intervention not found")

    old_status = it.status
    if body.status:
        st = body.status.upper()
        if st in ("OPEN", "IN_PROGRESS", "RESOLVED"):
            it.status = st
    if body.notes is not None:
        it.notes = body.notes
    if body.resolution is not None:
        it.resolution = body.resolution
        if it.resolution and it.status != "RESOLVED":
            it.status = "RESOLVED"
    if body.intervention_type is not None:
        it.intervention_type = body.intervention_type
    if body.recommendation is not None:
        it.recommendation = body.recommendation
    if body.risk_level is not None:
        it.risk_level = body.risk_level
    if body.follow_up_date is not None:
        if body.follow_up_date:
            try:
                it.follow_up_date = datetime.strptime(body.follow_up_date, "%Y-%m-%d").date()
            except ValueError:
                pass
        else:
            it.follow_up_date = None

    it.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(it)

    log_audit(
        db,
        actor=user,
        action="INTERVENTION_UPDATED",
        target_type="intervention",
        target_id=it.id,
        old_value={"status": old_status},
        new_value={"status": it.status, "notes": it.notes, "resolution": it.resolution},
    )

    emp = db.query(User).filter(User.id == it.employee_id).first()
    return {
        "ok": True,
        "id": f"INT-{it.id}",
        "raw_id": it.id,
        "employee": it.employee_name or (emp.name if emp else f"User {it.employee_id}"),
        "empId": emp.employee_code if emp else f"E{it.employee_id}",
        "department": emp.department if emp else "Engineering",
        "status": it.status,
        "risk_level": it.risk_level,
        "intervention_type": it.intervention_type,
        "trigger_reason": it.trigger_reason,
        "recommendation": it.recommendation,
        "notes": it.notes,
        "resolution": it.resolution,
        "follow_up_date": it.follow_up_date.strftime("%Y-%m-%d") if it.follow_up_date else "",
        "updated_at": it.updated_at.strftime("%d %b %Y, %I:%M %p"),
    }


# ===============================================================
# AI NLP & CHAT APIS
# ===============================================================

@app.post("/api/ai/analyze-text")
def ai_text(body: TextIn, user: User = Depends(current_user)):
    return analyze_communication(body.text)


@app.post("/api/ai/predict-burnout")
def ai_pred(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return recalculate_employee_burnout(db, user.id, trigger_source="api_request", actor=user, persist=True)


@app.post("/api/ai/chat")
def ai_chat(body: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    reply = process_chat_request(
        query=body.query_text,
        user=user,
        db=db,
        page_context=body.page_context,
        conversation_history=body.conversation_history,
    )
    return {"reply": reply}



# ===============================================================
# COMPANY SETTINGS & NOTIFICATIONS
# ===============================================================

@app.get("/api/settings/company")
def get_settings(db: Session = Depends(get_db)):
    s = get_company_settings(db)
    return {
        "work_start_time": s.work_start_time,
        "checkin_grace_time": s.checkin_grace_time,
        "afternoon_start_time": s.afternoon_start_time,
        "early_checkout_threshold": s.early_checkout_threshold,
        "work_end_time": s.work_end_time,
        "timezone": s.timezone,
        "survey_start_time": s.survey_start_time,
        "survey_end_time": s.survey_end_time,
    }


@app.put("/api/settings/company")
def update_settings(body: SettingsIn, user: User = Depends(require_role("hr")), db: Session = Depends(get_db)):
    s = get_company_settings(db)
    for field, val in body.model_dump(exclude_unset=True).items():
        if val is not None:
            setattr(s, field, val)
    db.commit()
    db.refresh(s)
    log_audit(db, actor=user, action="SETTINGS_UPDATED", target_type="company_settings", target_id=s.id)
    return {"ok": True, "settings": body.model_dump(exclude_unset=True)}


@app.get("/api/notifications")
def get_notifications_endpoint(
    include_archived: bool = Query(False),
    limit: int = Query(50),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Retrieve active notifications for the current authenticated user with 7-day read auto-archival."""
    return get_user_notifications(db=db, user=user, limit=limit, include_archived=include_archived)


@app.get("/api/notifications/unread-count")
def get_unread_notification_count_endpoint(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Fast scalar query for unread badge count."""
    return {"unread_count": get_unread_count(db=db, user=user)}


@app.post("/api/notifications/{notification_id}/read")
@app.patch("/api/notifications/{notification_id}/read")
def mark_notification_read_endpoint(
    notification_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Mark a notification as read with strict recipient authorization check."""
    try:
        notif = mark_notification_as_read(db=db, notification_id=notification_id, user=user)
        return {"ok": True, "id": notif.id, "is_read": True, "unread": False}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))


@app.post("/api/notifications/mark-all-read")
def mark_all_notifications_read_endpoint(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Mark all active notifications for the current authenticated user as read."""
    updated = mark_all_as_read(db=db, user=user)
    return {"ok": True, "marked_count": updated}


@app.post("/api/notifications/{notification_id}/archive")
def archive_notification_endpoint(
    notification_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Archive a notification for the current authenticated user."""
    try:
        notif = archive_notification(db=db, notification_id=notification_id, user=user)
        return {"ok": True, "id": notif.id, "is_archived": True}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))


@app.post("/api/notifications/cleanup")
def run_cleanup_endpoint(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Trigger retention policy cleanup (safe to call on demand or by scheduler)."""
    result = run_notification_retention_cleanup(db=db)
    return {"ok": True, **result}

