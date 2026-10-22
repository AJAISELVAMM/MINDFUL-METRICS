from __future__ import annotations
from datetime import datetime, date, time, timedelta
import pytz
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import Attendance, CompanySettings, LeaveRequest, PermissionRequest, User, Holiday, AttendanceCorrection
from .audit_service import log_audit


def get_company_settings(db: Session) -> CompanySettings:
    settings = db.query(CompanySettings).first()
    if not settings:
        settings = CompanySettings(
            work_start_time="09:00",
            checkin_grace_time="09:30",
            afternoon_start_time="13:00",
            early_checkout_threshold="17:00",
            work_end_time="17:30",
            timezone="Asia/Kolkata",
            survey_start_time="11:30",
            survey_end_time="15:00",
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def get_current_time(timezone_str: str = "Asia/Kolkata") -> datetime:
    try:
        tz = pytz.timezone(timezone_str)
        return datetime.now(tz)
    except Exception:
        return datetime.now()


def parse_time_str(t_str: str) -> time:
    """Parses 'HH:MM' or 'HH:MM AM/PM'."""
    t_str = t_str.strip()
    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p", "%H:%M:%S"):
        try:
            return datetime.strptime(t_str, fmt).time()
        except ValueError:
            pass
    return time(9, 0)


def fmt_12h(dt: datetime) -> str:
    return dt.strftime("%I:%M %p")


def calculate_attendance_rule(
    settings: CompanySettings,
    checkin_dt: datetime | None,
    checkout_dt: datetime | None,
    approved_leave: LeaveRequest | None = None,
    approved_permission: PermissionRequest | None = None,
) -> dict:
    """Pure calculation engine adhering strictly to Mindful Metrics specifications."""
    # Check for approved full-day leave
    if approved_leave and (approved_leave.half_day_session == "FULL_DAY" or not approved_leave.half_day_session):
        return {
            "arrival_status": None,
            "attendance_day_value": 0.0,
            "canonical_status": "ON_LEAVE",
            "morning_status": "APPROVED_LEAVE",
            "afternoon_status": "APPROVED_LEAVE",
            "final_status": "FULL_DAY_LEAVE",
            "exception_code": None,
            "working_minutes": 0,
            "overtime_minutes": 0,
            "late_minutes": 0,
            "early_checkout_minutes": 0,
        }

    # If no check-in at all
    if not checkin_dt:
        return {
            "arrival_status": None,
            "attendance_day_value": 0.0,
            "canonical_status": "ABSENT",
            "morning_status": "ABSENT",
            "afternoon_status": "ABSENT",
            "final_status": "ABSENT",
            "exception_code": None,
            "working_minutes": 0,
            "overtime_minutes": 0,
            "late_minutes": 0,
            "early_checkout_minutes": 0,
        }

    # Parse company thresholds
    t_start = parse_time_str(settings.work_start_time)
    t_grace = parse_time_str(settings.checkin_grace_time)
    t_threshold = parse_time_str(settings.early_checkout_threshold)
    t_end = parse_time_str(settings.work_end_time)

    # 1. MORNING ATTENDANCE
    has_morning_leave = approved_leave and approved_leave.half_day_session == "MORNING_HALF_DAY"
    has_afternoon_leave = approved_leave and approved_leave.half_day_session == "AFTERNOON_HALF_DAY"

    checkin_time = checkin_dt.time()
    start_dt = checkin_dt.replace(hour=t_start.hour, minute=t_start.minute, second=0, microsecond=0)

    if has_morning_leave:
        morning_status = "APPROVED_MORNING_LEAVE"
        arrival_status = "ON_TIME"
        late_minutes = 0
    elif checkin_time <= t_grace:
        morning_status = "PRESENT"
        arrival_status = "ON_TIME"
        late_minutes = 0  # Inclusive cutoff: arrivals up to 09:30 AM are on-time
    else:
        morning_status = "MORNING_HALF_DAY_ABSENT"
        arrival_status = "LATE"
        late_minutes = int((checkin_dt - start_dt).total_seconds() / 60)

    # If no checkout yet (currently on duty / working)
    if not checkout_dt:
        return {
            "arrival_status": arrival_status,
            "attendance_day_value": 0.5 if arrival_status == "LATE" else 1.0,
            "canonical_status": "PRESENT",
            "morning_status": morning_status,
            "afternoon_status": "PENDING",
            "final_status": "INCOMPLETE",
            "exception_code": None,
            "working_minutes": 0,
            "overtime_minutes": 0,
            "late_minutes": late_minutes,
            "early_checkout_minutes": 0,
        }

    # 2. WORKING MINUTES
    working_sec = max(0, (checkout_dt - checkin_dt).total_seconds())
    working_minutes = int(working_sec / 60)

    # 3. OVERTIME (strictly after configured end time, e.g. 17:30)
    end_dt = checkout_dt.replace(hour=t_end.hour, minute=t_end.minute, second=0, microsecond=0)
    threshold_dt = checkout_dt.replace(hour=t_threshold.hour, minute=t_threshold.minute, second=0, microsecond=0)

    checkout_time = checkout_dt.time()
    overtime_minutes = 0
    if checkout_dt > end_dt:
        overtime_minutes = int((checkout_dt - end_dt).total_seconds() / 60)

    # 4. AFTERNOON ATTENDANCE
    early_checkout_minutes = 0
    if checkout_time >= t_threshold:
        # Checkout between 17:00 and 17:30 OR after 17:30
        afternoon_status = "PRESENT"
    else:
        # Checkout before 17:00
        early_checkout_minutes = int((threshold_dt - checkout_dt).total_seconds() / 60)
        if approved_permission:
            afternoon_status = "APPROVED_PERMISSION"
        elif has_afternoon_leave:
            afternoon_status = "APPROVED_AFTERNOON_LEAVE"
        else:
            afternoon_status = "UNAUTHORIZED_EARLY_CHECKOUT"

    # 5. FINAL ATTENDANCE STATUS & ATTENDANCE-DAY CREDIT
    exception_code = None
    if working_minutes < 30 and not approved_permission and not approved_leave:
        final_status = "ATTENDANCE_EXCEPTION"
        afternoon_status = "SHORT_SESSION_EXCEPTION"
        canonical_status = "ABSENT"
        attendance_day_value = 0.0
        exception_code = "SHORT_SESSION_EXCEPTION"
    elif morning_status == "PRESENT":
        if afternoon_status == "PRESENT":
            final_status = "FULL_DAY_PRESENT"
            canonical_status = "PRESENT"
            attendance_day_value = 1.0
        elif afternoon_status == "APPROVED_PERMISSION":
            final_status = "PRESENT_WITH_APPROVED_PERMISSION"
            canonical_status = "PRESENT"
            attendance_day_value = 1.0
        elif afternoon_status == "APPROVED_AFTERNOON_LEAVE":
            final_status = "HALF_DAY_LEAVE"
            canonical_status = "HALF_DAY"
            attendance_day_value = 0.5
        elif afternoon_status == "UNAUTHORIZED_EARLY_CHECKOUT":
            final_status = "ATTENDANCE_EXCEPTION"
            canonical_status = "HALF_DAY"  # Early departure ineligible for full day; earns half-day
            attendance_day_value = 0.5
            exception_code = "UNAUTHORIZED_EARLY_CHECKOUT"
        else:
            final_status = "ATTENDANCE_EXCEPTION"
            canonical_status = "HALF_DAY"
            attendance_day_value = 0.5
    elif morning_status == "MORNING_HALF_DAY_ABSENT":
        # Late arrival (> 09:30)
        if afternoon_status in ("PRESENT", "APPROVED_PERMISSION"):
            final_status = "MORNING_HALF_DAY_ABSENT"
            canonical_status = "HALF_DAY"  # Configured half-day policy for late arrival with checkout >= 17:00
            attendance_day_value = 0.5
        elif afternoon_status == "APPROVED_AFTERNOON_LEAVE":
            final_status = "HALF_DAY_LEAVE"
            canonical_status = "HALF_DAY"
            attendance_day_value = 0.5
        else:
            final_status = "ATTENDANCE_EXCEPTION"
            canonical_status = "ABSENT"  # Late arrival + unapproved early departure earns 0.0 credit
            attendance_day_value = 0.0
            exception_code = "LATE_AND_EARLY_CHECKOUT"
    elif morning_status == "APPROVED_MORNING_LEAVE":
        final_status = "HALF_DAY_LEAVE"
        canonical_status = "HALF_DAY"
        attendance_day_value = 0.5
    else:
        final_status = "ATTENDANCE_EXCEPTION"
        canonical_status = "ABSENT"
        attendance_day_value = 0.0

    return {
        "arrival_status": arrival_status,
        "attendance_day_value": attendance_day_value,
        "canonical_status": canonical_status,
        "morning_status": morning_status,
        "afternoon_status": afternoon_status,
        "final_status": final_status,
        "exception_code": exception_code,
        "working_minutes": working_minutes,
        "overtime_minutes": overtime_minutes,
        "late_minutes": late_minutes,
        "early_checkout_minutes": early_checkout_minutes,
    }


def get_canonical_attendance_status(
    att: Attendance | None,
    is_holiday: bool = False,
    is_weekly_off: bool = False,
    has_leave: bool = False,
    is_future: bool = False,
    is_today_open: bool = False,
) -> tuple[str, str, float]:
    """
    Authoritative status synchronizer across Weekly Attendance, Calendar, and Summary Cards.
    Returns: (canonical_status, display_status, attendance_day_value)
    
    Status codes guaranteed 1:1 match:
    - PRESENT
    - HALF_DAY
    - LATE
    - ABSENT
    - ON_LEAVE
    - HOLIDAY
    - WEEKLY_OFF
    - FUTURE
    - PENDING
    - EXCEPTION
    """
    if isinstance(is_holiday, tuple):
        is_holiday = bool(is_holiday[0])
    else:
        is_holiday = bool(is_holiday)

    if isinstance(is_weekly_off, tuple):
        is_weekly_off = bool(is_weekly_off[0])
    else:
        is_weekly_off = bool(is_weekly_off)

    has_leave = bool(has_leave)
    is_future = bool(is_future)
    is_today_open = bool(is_today_open)

    from .holiday_service import is_weekly_off as check_sunday
    if att and att.date and check_sunday(att.date):
        is_weekly_off = True

    if att:
        if att.final_status == "HOLIDAY" or (is_holiday and not att.check_in_at):
            return "HOLIDAY", "Holiday", 0.0
        if att.final_status == "WEEKLY_OFF" or (is_weekly_off and not att.check_in_at):
            return "WEEKLY_OFF", "Weekly Off", 0.0
        if att.final_status in ("FULL_DAY_LEAVE", "LEAVE") or (has_leave and not att.check_in_at):
            return "ON_LEAVE", "On Leave", 0.0
        if att.final_status in ("HALF_DAY_LEAVE", "MORNING_HALF_DAY_ABSENT", "HALF_DAY"):
            return "HALF_DAY", "Half-Day", 0.5
        if att.final_status in ("FULL_DAY_PRESENT", "PRESENT_WITH_APPROVED_PERMISSION", "LATE_PRESENT", "PRESENT"):
            return "PRESENT", "Present", 1.0
        if att.final_status == "WORKING":
            return ("PRESENT", "Present", 1.0) if (att.check_in_at or att.check_in) else ("PENDING", "Working", 0.0)
        if att.final_status == "ABSENT":
            return "ABSENT", "Absent", 0.0
        if att.final_status == "ATTENDANCE_EXCEPTION":
            if (att.attendance_day_value or 0) >= 0.5:
                return "HALF_DAY", "Half-Day", 0.5
            return "EXCEPTION", "Exception", 0.0
        if att.status:
            if "Present" in att.status:
                return "PRESENT", "Present", 1.0
            if "Half" in att.status:
                return "HALF_DAY", "Half-Day", 0.5
            if "Leave" in att.status:
                return "ON_LEAVE", "On Leave", 0.0
            if "Holiday" in att.status:
                return "HOLIDAY", "Holiday", 0.0
            if "Weekly" in att.status:
                return "WEEKLY_OFF", "Weekly Off", 0.0
            if "Absent" in att.status:
                return "ABSENT", "Absent", 0.0
        return "PRESENT", "Present", 1.0

    # No attendance record exists
    if is_holiday:
        return "HOLIDAY", "Holiday", 0.0
    if is_weekly_off:
        return "WEEKLY_OFF", "Weekly Off", 0.0
    if has_leave:
        return "ON_LEAVE", "On Leave", 0.0
    if is_future:
        return "FUTURE", "Upcoming", 0.0
    if is_today_open:
        return "PENDING", "Working Today", 0.0
    return "ABSENT", "Absent", 0.0


def find_approved_leave_for_date(db: Session, employee_id: int, target_date: date) -> LeaveRequest | None:
    return (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status == "Approved",
            (
                (LeaveRequest.start_date <= target_date) & (LeaveRequest.end_date >= target_date)
                | (LeaveRequest.date.like(f"%{target_date.strftime('%d %b')}%"))
                | (LeaveRequest.date.like(f"%{target_date.strftime('%Y-%m-%d')}%"))
            ),
        )
        .first()
    )


def find_approved_permission_for_date(db: Session, employee_id: int, target_date: date) -> PermissionRequest | None:
    return (
        db.query(PermissionRequest)
        .filter(
            PermissionRequest.employee_id == employee_id,
            PermissionRequest.status == "Approved",
            PermissionRequest.date == target_date,
        )
        .first()
    )


def check_in_user(
    db: Session,
    user: User,
    override_now: datetime | None = None,
    survey_answers: dict | None = None,
) -> dict:
    settings = get_company_settings(db)
    now = override_now or get_current_time(settings.timezone)
    today = now.date()

    existing = db.query(Attendance).filter(Attendance.employee_id == user.id, Attendance.date == today).first()
    if existing and existing.check_in_at:
        return {
            "error": "Already checked in today",
            "checkInTime": existing.check_in,
            "status": existing.final_status,
        }

    # If already finalized as Absent at 7 PM cutoff
    if existing and existing.final_status == "ABSENT":
        return {
            "error": "Attendance for today was finalized as Absent at 7:00 PM. Website login or late check-in cannot alter finalized attendance. Please submit an HR attendance correction request if you were present.",
            "status": "ABSENT",
        }

    # Check 7:00 PM cutoff (Night login behavior)
    if now.time() >= time(19, 0):
        return {
            "error": "The daily attendance check-in window closed at 7:00 PM. Please submit an HR attendance correction request.",
            "status": "ATTENDANCE_WINDOW_CLOSED",
        }

    # Check if today is an applicable company holiday
    from .holiday_service import is_holiday
    is_h, holiday_obj = is_holiday(db, today, calendar_type="company")
    if is_h and not existing:
        return {
            "error": f"Today is an official holiday: {holiday_obj.holiday_name}. Regular check-in is not required.",
            "status": "HOLIDAY",
        }

    # Check for approved full-day leave
    app_leave = find_approved_leave_for_date(db, user.id, today)
    if app_leave and (app_leave.half_day_session == "FULL_DAY" or not app_leave.half_day_session):
        return {
            "error": "Cannot check in: Approved full-day leave is registered for today.",
            "status": "FULL_DAY_LEAVE",
        }

    # Save morning survey if provided
    if survey_answers:
        try:
            from .survey_service import submit_daily_survey
            submit_daily_survey(db, user, answers=survey_answers, survey_type="morning")
        except Exception:
            pass

    calc = calculate_attendance_rule(settings, checkin_dt=now, checkout_dt=None, approved_leave=app_leave)

    formatted_time = fmt_12h(now)
    if not existing:
        existing = Attendance(
            employee_id=user.id,
            date=today,
            check_in=formatted_time,
            check_in_at=now.replace(tzinfo=None) if now.tzinfo else now,
            morning_status=calc["morning_status"],
            afternoon_status="PENDING",
            final_status="WORKING",
            arrival_status=calc["arrival_status"],
            attendance_day_value=calc["attendance_day_value"],
            late_minutes=calc["late_minutes"],
            approved_leave_id=app_leave.id if app_leave else None,
            status="Working",
        )
        db.add(existing)
    else:
        existing.check_in = formatted_time
        existing.check_in_at = now.replace(tzinfo=None) if now.tzinfo else now
        existing.morning_status = calc["morning_status"]
        existing.final_status = "WORKING"
        existing.arrival_status = calc["arrival_status"]
        existing.attendance_day_value = calc["attendance_day_value"]
        existing.late_minutes = calc["late_minutes"]
        existing.status = "Working"

    db.commit()
    db.refresh(existing)

    log_audit(
        db,
        actor=user,
        action="CHECK_IN",
        target_type="attendance",
        target_id=existing.id,
        new_value={"time": formatted_time, "morning_status": existing.morning_status, "arrival_status": existing.arrival_status},
    )

    pred = None
    try:
        from .burnout_service import recalculate_employee_burnout
        pred = recalculate_employee_burnout(db, user.id, trigger_source="check_in", actor=user, persist=True)
    except Exception:
        pass

    return {
        "ok": True,
        "time": formatted_time,
        "date": today.isoformat(),
        "arrival_status": existing.arrival_status,
        "attendance_day_value": existing.attendance_day_value,
        "morning_status": existing.morning_status,
        "status": existing.final_status,
        "canonical_status": calc.get("canonical_status", "PRESENT"),
        "late_minutes": existing.late_minutes,
        "message": "You're checked in successfully.",
        "prediction": pred,
    }


def check_out_user(
    db: Session,
    user: User,
    override_now: datetime | None = None,
    survey_answers: dict | None = None,
    note: str | None = None,
) -> dict:
    settings = get_company_settings(db)
    now = override_now or get_current_time(settings.timezone)
    today = now.date()

    existing = db.query(Attendance).filter(Attendance.employee_id == user.id, Attendance.date == today).first()
    if not existing or not existing.check_in_at:
        return {"error": "Check in first before checking out."}
    if existing.check_out_at:
        return {"error": "Already checked out today."}

    # Save evening survey if provided
    if survey_answers:
        try:
            from .survey_service import submit_daily_survey
            submit_daily_survey(db, user, answers=survey_answers, note=note, survey_type="evening")
        except Exception:
            pass

    app_leave = find_approved_leave_for_date(db, user.id, today)
    app_perm = find_approved_permission_for_date(db, user.id, today)

    checkin_dt = existing.check_in_at
    if now.tzinfo:
        now_naive = now.replace(tzinfo=None)
    else:
        now_naive = now

    calc = calculate_attendance_rule(
        settings,
        checkin_dt=checkin_dt,
        checkout_dt=now_naive,
        approved_leave=app_leave,
        approved_permission=app_perm,
    )

    formatted_time = fmt_12h(now)
    h = calc["working_minutes"] // 60
    m = calc["working_minutes"] % 60
    working_hours_str = f"{h:02d}h {m:02d}m"

    ot_h = calc["overtime_minutes"] // 60
    ot_m = calc["overtime_minutes"] % 60
    overtime_str = f"{ot_h:02d}h {ot_m:02d}m"

    existing.check_out = formatted_time
    existing.check_out_at = now_naive
    existing.morning_status = calc["morning_status"]
    existing.afternoon_status = calc["afternoon_status"]
    existing.final_status = calc["final_status"]
    existing.arrival_status = calc["arrival_status"]
    existing.attendance_day_value = calc["attendance_day_value"]
    existing.working_minutes = calc["working_minutes"]
    existing.overtime_minutes = calc["overtime_minutes"]
    existing.early_checkout_minutes = calc["early_checkout_minutes"]
    existing.approved_leave_id = app_leave.id if app_leave else None
    existing.approved_permission_id = app_perm.id if app_perm else None
    existing.status = "Completed"

    db.commit()
    db.refresh(existing)

    log_audit(
        db,
        actor=user,
        action="CHECK_OUT",
        target_type="attendance",
        target_id=existing.id,
        new_value={
            "time": formatted_time,
            "final_status": existing.final_status,
            "arrival_status": existing.arrival_status,
            "attendance_day_value": existing.attendance_day_value,
            "working_minutes": existing.working_minutes,
            "overtime_minutes": existing.overtime_minutes,
        },
    )

    pred = None
    try:
        from .burnout_service import recalculate_employee_burnout
        pred = recalculate_employee_burnout(db, user.id, trigger_source="check_out", actor=user, persist=True)
    except Exception:
        pass

    return {
        "ok": True,
        "time": formatted_time,
        "workingHours": working_hours_str,
        "overtime": overtime_str,
        "working_minutes": calc["working_minutes"],
        "overtime_minutes": calc["overtime_minutes"],
        "arrival_status": calc["arrival_status"],
        "attendance_day_value": calc["attendance_day_value"],
        "morning_status": calc["morning_status"],
        "afternoon_status": calc["afternoon_status"],
        "final_status": calc["final_status"],
        "canonical_status": calc.get("canonical_status", "PRESENT"),
        "status": existing.status,
        "message": f"Checked out at {formatted_time}. Total hours: {working_hours_str}.",
        "prediction": pred,
    }


def get_today_attendance_record(db: Session, user: User) -> dict:
    settings = get_company_settings(db)
    now = get_current_time(settings.timezone)
    today = now.date()

    rec = db.query(Attendance).filter(Attendance.employee_id == user.id, Attendance.date == today).first()
    from ..models import Prediction
    latest_pred = db.query(Prediction).filter(Prediction.employee_id == user.id).order_by(Prediction.id.desc()).first()
    if not latest_pred:
        try:
            from .burnout_service import predict_for_employee
            p_gen = predict_for_employee(db, user, persist=True)
            if not p_gen.get("insufficient_data"):
                latest_pred = db.query(Prediction).filter(Prediction.employee_id == user.id).order_by(Prediction.id.desc()).first()
        except Exception:
            pass

    b_score = int(round(latest_pred.burnout_score)) if latest_pred and latest_pred.burnout_score is not None else None
    b_level = latest_pred.risk_level if latest_pred else None
    b_recs = latest_pred.recommendations if latest_pred and latest_pred.recommendations else []
    b_rec = b_recs[0] if b_recs else None

    if not rec:
        # Check if full day leave
        app_leave = find_approved_leave_for_date(db, user.id, today)
        if app_leave:
            return {
                "checkedIn": False,
                "checkedOut": False,
                "phase": "ON_LEAVE",
                "final_status": "FULL_DAY_LEAVE",
                "leave": app_leave.type,
                "burnout_score": b_score,
                "burnout_level": b_level,
                "burnout_rec": b_rec,
                "userId": user.id,
            }
        return {
            "checkedIn": False,
            "checkedOut": False,
            "phase": "NOT_CHECKED_IN",
            "checkInTime": None,
            "checkOutTime": None,
            "workingHours": None,
            "overtime": None,
            "final_status": "NOT_STARTED",
            "burnout_score": b_score,
            "burnout_level": b_level,
            "burnout_rec": b_rec,
            "userId": user.id,
        }

    h = rec.working_minutes // 60 if rec.working_minutes else 0
    m = rec.working_minutes % 60 if rec.working_minutes else 0
    ot_h = rec.overtime_minutes // 60 if rec.overtime_minutes else 0
    ot_m = rec.overtime_minutes % 60 if rec.overtime_minutes else 0

    return {
        "checkedIn": bool(rec.check_in_at or rec.check_in),
        "checkedOut": bool(rec.check_out_at or rec.check_out),
        "phase": "DAY_COMPLETED" if rec.check_out else "WORKING",
        "checkInTime": rec.check_in,
        "checkOutTime": rec.check_out,
        "workingHours": f"{h:02d}h {m:02d}m" if rec.working_minutes is not None else "—",
        "overtime": f"{ot_h:02d}h {ot_m:02d}m" if rec.overtime_minutes is not None else "—",
        "working_minutes": rec.working_minutes,
        "overtime_minutes": rec.overtime_minutes,
        "morning_status": rec.morning_status,
        "afternoon_status": rec.afternoon_status,
        "final_status": rec.final_status,
        "status": rec.status,
        "burnout_score": b_score,
        "burnout_level": b_level,
        "burnout_rec": b_rec,
        "userId": user.id,
    }


def get_user_attendance_history(db: Session, user: User, limit: int = 14) -> dict:
    rows = (
        db.query(Attendance)
        .filter(Attendance.employee_id == user.id)
        .order_by(Attendance.date.desc())
        .limit(limit)
        .all()
    )

    weekly = []
    for a in rows:
        h = a.working_minutes // 60 if a.working_minutes else 0
        m = a.working_minutes % 60 if a.working_minutes else 0
        ot_h = a.overtime_minutes // 60 if a.overtime_minutes else 0
        ot_m = a.overtime_minutes % 60 if a.overtime_minutes else 0

        canon_status, disp_status, day_val = get_canonical_attendance_status(a)
        arr_status = a.arrival_status or ("LATE" if (a.late_minutes or 0) > 0 else "ON_TIME" if a.check_in else "—")

        weekly.append({
            "date": a.date.strftime("%d %b"),
            "full_date": a.date.isoformat(),
            "checkIn": a.check_in or "—",
            "checkOut": a.check_out or "—",
            "hours": f"{h:02d}h {m:02d}m" if a.working_minutes else "—",
            "overtime": f"{ot_h:02d}h {ot_m:02d}m" if a.overtime_minutes else "—",
            "status": canon_status,
            "display_status": disp_status,
            "canonical_status": canon_status,
            "morning_status": a.morning_status or "—",
            "afternoon_status": a.afternoon_status or "—",
            "final_status": a.final_status or "—",
            "arrival_status": arr_status,
            "attendance_day_value": a.attendance_day_value if a.attendance_day_value is not None else day_val,
            "working_minutes": a.working_minutes,
            "overtime_minutes": a.overtime_minutes,
        })

    # Authoritative monthly aggregations for THIS specific authenticated user
    month_metrics = get_attendance_summary_metrics(
        db, user, target_date=None, year=date.today().year, month=date.today().month, target_user_id=user.id
    )
    return {"weekly": weekly, "monthly": month_metrics}


def get_attendance_summary_metrics(
    db: Session,
    user: User,
    target_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
    department: str | None = None,
    target_user_id: int | None = None,
) -> dict:
    """
    Computes dynamic SQL aggregates for the 6 Mindful Metrics dashboard cards:
    1. Present (records with valid full-day present status or completed credit)
    2. Absent (confirmed ordinary absences, excluding weekly offs, holidays, leaves, future dates)
    3. Late (records whose arrival status is LATE or late_minutes > 0)
    4. On Leave (approved leaves, deduplicated with attendance rows)
    5. Average Hours (sum(working_minutes) / (completed_count * 60))
    6. OT Hours (sum(overtime_minutes) / 60)
    
    Role Scoping:
    - Employee: Scoped strictly to self (target_user_id is ignored or forced to user.id)
    - Manager: If target_user_id provided, scoped to authorized member/self; else scoped to department team
    - HR: If target_user_id provided, scoped to that employee; else scoped to org / department
    """
    settings = get_company_settings(db)
    now = get_current_time(settings.timezone)
    today = now.date()

    # Determine date range
    if target_date:
        start_d = target_date
        end_d = target_date
    elif year and month:
        import calendar
        _, last_day = calendar.monthrange(year, month)
        start_d = date(year, month, 1)
        end_d = date(year, month, last_day)
    else:
        # Default: current month
        start_d = today.replace(day=1)
        end_d = today

    # Base query for attendance
    query = db.query(Attendance).join(User, Attendance.employee_id == User.id)

    # Scoping
    scoped_emp_id = None
    if user.role == "employee":
        scoped_emp_id = user.id
    elif user.role == "manager":
        if target_user_id:
            target_user = db.query(User).filter(User.id == target_user_id).first()
            if target_user and (target_user.department == user.department or target_user.id == user.id):
                scoped_emp_id = target_user_id
            else:
                department = user.department
        else:
            department = user.department
    elif user.role == "hr":
        if target_user_id:
            scoped_emp_id = target_user_id

    if scoped_emp_id:
        query = query.filter(Attendance.employee_id == scoped_emp_id)
    elif user.role == "manager":
        query = query.filter((Attendance.employee_id == user.id) | (User.department == user.department))
    elif user.role == "hr":
        if department and department.lower() != "all":
            query = query.filter(User.department.ilike(department))
    
    # Date filtering
    query = query.filter(Attendance.date >= start_d, Attendance.date <= end_d)
    records = query.all()

    present_count = 0
    half_day_count = 0
    absent_count = 0
    late_count = 0
    leave_count = 0
    total_working_min = 0
    completed_count = 0
    total_ot_min = 0
    counted_leave_emp_dates = set()

    for a in records:
        canon_status, disp_status, val = get_canonical_attendance_status(a)
        
        # 1. Present: count eligible full-day present records
        if canon_status == "PRESENT":
            present_count += 1
        elif canon_status == "HALF_DAY":
            half_day_count += 1

        # 2. Absent: confirmed ordinary absences (excludes holidays, Sundays, approved leaves, future dates)
        if canon_status == "ABSENT":
            absent_count += 1

        # 3. Late: records whose authoritative arrival status is LATE
        if a.arrival_status == "LATE" or (a.late_minutes and a.late_minutes > 0):
            late_count += 1

        # 4. On Leave from attendance records
        if canon_status == "ON_LEAVE" or "LEAVE" in (a.final_status or "") or a.approved_leave_id:
            leave_count += 1
            counted_leave_emp_dates.add((a.employee_id, a.date))

        # 5. Working duration from valid completed records
        if a.working_minutes and a.working_minutes > 0 and (a.check_out_at is not None or a.check_out is not None or a.status == "Completed"):
            total_working_min += a.working_minutes
            completed_count += 1

        # 6. Overtime from valid timestamps
        if a.overtime_minutes and a.overtime_minutes > 0:
            total_ot_min += a.overtime_minutes

    # Approved leave requests check (to count approved leaves within date range not in attendance)
    leave_query = db.query(LeaveRequest).join(User, LeaveRequest.employee_id == User.id).filter(
        LeaveRequest.status == "Approved",
        LeaveRequest.start_date <= end_d,
        LeaveRequest.end_date >= start_d,
    )
    if scoped_emp_id:
        leave_query = leave_query.filter(LeaveRequest.employee_id == scoped_emp_id)
    elif user.role == "manager":
        leave_query = leave_query.filter((LeaveRequest.employee_id == user.id) | (User.department == user.department))
    elif user.role == "hr":
        if department and department.lower() != "all":
            leave_query = leave_query.filter(User.department.ilike(department))
    
    app_leaves = leave_query.all()
    for l in app_leaves:
        if l.start_date and l.end_date:
            cur = max(start_d, l.start_date)
            fin = min(end_d, l.end_date)
            while cur <= fin:
                if (l.employee_id, cur) not in counted_leave_emp_dates:
                    leave_count += 1
                    counted_leave_emp_dates.add((l.employee_id, cur))
                cur += timedelta(days=1)

    avg_hours = round(total_working_min / (completed_count * 60), 1) if completed_count > 0 else 0.0
    ot_hours = round(total_ot_min / 60, 1)

    return {
        "present": present_count,
        "halfDay": half_day_count,
        "attendanceCredit": round(present_count * 1.0 + half_day_count * 0.5, 1),
        "absent": absent_count,
        "late": late_count,
        "onLeave": leave_count,
        "avgHours": avg_hours,
        "otHours": ot_hours,
        "overtimeHours": ot_hours,
        "completedRecords": completed_count,
        "totalRecords": len(records),
        "filter": {
            "startDate": start_d.isoformat(),
            "endDate": end_d.isoformat(),
            "department": department or "All",
            "role": user.role,
        },
    }


def get_attendance_calendar_feed(
    db: Session,
    user: User,
    year: int,
    month: int,
    target_user_id: int | None = None,
) -> list[dict]:
    """
    Returns the real calendar feed for the given year and month.
    Each day includes:
    - date, day of month, day of week
    - is_weekly_off (automatic recurring Sunday rule)
    - is_holiday (active company holiday from PostgreSQL)
    - status: 'PRESENT', 'HALF_DAY', 'LATE', 'ABSENT', 'ON_LEAVE', 'HOLIDAY', 'WEEKLY_OFF', 'FUTURE', 'PENDING'
    - checkIn, checkOut, workingHours, lateMinutes
    - arrival_status: 'ON_TIME' or 'LATE'
    - attendance_day_value: 1.0, 0.5, 0.0
    - badge label
    """
    import calendar
    from .holiday_service import is_holiday, is_weekly_off

    settings = get_company_settings(db)
    now = get_current_time(settings.timezone)
    today = now.date()

    # Role-based authorization on target_user_id
    scoped_emp_id = user.id
    if target_user_id and target_user_id != user.id:
        if user.role == "hr":
            scoped_emp_id = target_user_id
        elif user.role == "manager":
            target_user = db.query(User).filter(User.id == target_user_id).first()
            if target_user and target_user.department == user.department:
                scoped_emp_id = target_user_id

    _, num_days = calendar.monthrange(year, month)
    start_d = date(year, month, 1)
    end_d = date(year, month, num_days)

    # Fetch all attendance records for this user in this month
    records = {
        a.date: a
        for a in db.query(Attendance)
        .filter(Attendance.employee_id == scoped_emp_id, Attendance.date >= start_d, Attendance.date <= end_d)
        .all()
    }

    # Fetch all approved leaves for this user in this month
    leaves = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == scoped_emp_id,
            LeaveRequest.status == "Approved",
            LeaveRequest.start_date <= end_d,
            LeaveRequest.end_date >= start_d,
        )
        .all()
    )

    # Fetch all holidays for this month in one single query
    month_holidays = {
        h.holiday_date: h
        for h in db.query(Holiday)
        .filter(
            Holiday.holiday_date >= start_d,
            Holiday.holiday_date <= end_d,
            Holiday.is_active == 1,
            Holiday.applicability.in_(["all", "company"]),
        )
        .all()
    }

    days_feed = []

    for day in range(1, num_days + 1):
        cur_date = date(year, month, day)
        is_sunday = is_weekly_off(cur_date)
        hol_obj = month_holidays.get(cur_date)
        is_h = hol_obj is not None
        is_future = cur_date > today
        att = records.get(cur_date)

        # Check approved leave on this date
        has_leave = False
        leave_label = "On Leave"
        for l in leaves:
            if l.start_date and l.end_date and l.start_date <= cur_date <= l.end_date:
                has_leave = True
                leave_label = f"Leave ({l.leave_type})" if l.leave_type else "On Leave"
                break

        canon_status, disp_status, day_val = get_canonical_attendance_status(
            att,
            is_holiday=is_h,
            is_weekly_off=is_sunday,
            has_leave=has_leave,
            is_future=is_future,
            is_today_open=(cur_date == today and now.time() < time(19, 0)),
        )

        badge = (
            f"Holiday: {hol_obj.holiday_name}" if is_h
            else leave_label if has_leave
            else disp_status
        )

        w_min = att.working_minutes if att else None
        h_str = f"{w_min // 60}h {w_min % 60}m" if (w_min is not None and w_min > 0) else None

        days_feed.append({
            "date": cur_date.isoformat(),
            "day": day,
            "weekday": cur_date.strftime("%a"),
            "status": canon_status,
            "canonical_status": canon_status,
            "display_status": disp_status,
            "badge": badge,
            "isWeeklyOff": is_sunday,
            "isHoliday": is_h,
            "holidayName": hol_obj.holiday_name if is_h else None,
            "isFuture": is_future,
            "checkIn": att.check_in if att else None,
            "checkOut": att.check_out if att else None,
            "workingHours": h_str,
            "lateMinutes": att.late_minutes if att else 0,
            "arrival_status": att.arrival_status if att else None,
            "attendance_day_value": att.attendance_day_value if att and att.attendance_day_value is not None else day_val,
            "finalStatus": att.final_status if att else canon_status,
        })

    return days_feed


def finalize_daily_attendance(db: Session, target_date: date | None = None, force: bool = False, allow_future: bool = False) -> dict:
    """
    Daily attendance finalization at 7:00 PM (Asia/Kolkata).
    - Checks weekly offs (Sundays).
    - Checks active Tamil Nadu Government public holidays (excluding bank-only holidays for general employees).
    - Checks approved full-day and half-day leaves.
    - If employee checked in but missed checkout, sets missing checkout / exception.
    - If no check-in and no approved exception/holiday/leave, finalizes attendance as ABSENT.
    - Recalculates burnout risk prediction.
    - Idempotent and safe across multiple workers.
    """
    settings = get_company_settings(db)
    now = get_current_time(settings.timezone)
    today = now.date()
    eval_date = target_date or today

    if eval_date > today and not allow_future:
        return {"ok": False, "error": "Cannot finalize attendance for future dates.", "finalized_count": 0}

    # Cutoff check: If finalizing today and not forced, ensure 7:00 PM cutoff has passed
    if eval_date == today and not force and now.time() < time(19, 0):
        return {
            "ok": False,
            "error": f"Attendance cutoff is 7:00 PM (Asia/Kolkata). Current time {now.strftime('%I:%M %p')} has not reached cutoff yet.",
            "finalized_count": 0,
        }

    from .holiday_service import is_holiday, is_weekly_off
    from .burnout_service import predict_for_employee, recalculate_employee_burnout

    is_h, holiday_obj = is_holiday(db, eval_date, calendar_type="company")
    is_wo = is_weekly_off(eval_date)

    users = db.query(User).filter(User.role.in_(["employee", "manager"])).all()

    finalized_absent = 0
    finalized_holiday = 0
    finalized_weekly_off = 0
    finalized_leave = 0
    finalized_missing_checkout = 0
    unchanged = 0
    newly_affected_users = []

    for u in users:
        existing = db.query(Attendance).filter(Attendance.employee_id == u.id, Attendance.date == eval_date).first()

        if existing:
            # 1. Already finalized or completed with both check-in and check-out
            if existing.final_status in (
                "FULL_DAY_PRESENT", "PRESENT_WITH_APPROVED_PERMISSION", "LATE_PRESENT",
                "HALF_DAY_LEAVE", "FULL_DAY_LEAVE", "HOLIDAY", "WEEKLY_OFF", "ABSENT"
            ) or (existing.check_in_at and existing.check_out_at):
                unchanged += 1
                continue

            # 2. Incomplete checkout (checked in but never checked out)
            if existing.check_in_at and not existing.check_out_at:
                existing.afternoon_status = "MISSING_CHECKOUT"
                existing.final_status = "ATTENDANCE_EXCEPTION"
                existing.status = "Exception"
                existing.attendance_day_value = 0.5 if existing.arrival_status == "ON_TIME" else 0.0
                existing.finalized_at = now.replace(tzinfo=None) if now.tzinfo else now
                finalized_missing_checkout += 1
                try:
                    recalculate_employee_burnout(db, u.id, trigger_source="attendance_finalized", persist=True)
                except Exception:
                    pass
                continue

            # 3. Existing record without check-in: update in place to avoid duplicate key error
            fin_time = now.replace(tzinfo=None) if now.tzinfo else now
            if is_wo and is_h:
                hol_name = holiday_obj.holiday_name if holiday_obj else "Public Holiday"
                existing.final_status = "HOLIDAY"
                existing.morning_status = "HOLIDAY"
                existing.afternoon_status = "WEEKLY_OFF"
                existing.arrival_status = "ON_TIME"
                existing.attendance_day_value = 0.0
                existing.finalized_at = fin_time
                existing.status = f"Holiday ({hol_name})"
                existing.working_minutes = 0
                finalized_holiday += 1
                continue

            if is_wo:
                existing.final_status = "WEEKLY_OFF"
                existing.morning_status = "WEEKLY_OFF"
                existing.afternoon_status = "WEEKLY_OFF"
                existing.arrival_status = "ON_TIME"
                existing.attendance_day_value = 0.0
                existing.finalized_at = fin_time
                existing.status = "Weekly Off"
                existing.working_minutes = 0
                finalized_weekly_off += 1
                continue

            if is_h:
                hol_name = holiday_obj.holiday_name if holiday_obj else "Public Holiday"
                existing.final_status = "HOLIDAY"
                existing.morning_status = "HOLIDAY"
                existing.afternoon_status = "HOLIDAY"
                existing.arrival_status = "ON_TIME"
                existing.attendance_day_value = 0.0
                existing.finalized_at = fin_time
                existing.status = f"Holiday ({hol_name})"
                existing.working_minutes = 0
                finalized_holiday += 1
                continue

            app_leave = find_approved_leave_for_date(db, u.id, eval_date)
            if app_leave:
                is_full = (app_leave.half_day_session == "FULL_DAY" or not app_leave.half_day_session)
                existing.final_status = "FULL_DAY_LEAVE" if is_full else "HALF_DAY_LEAVE"
                existing.morning_status = "APPROVED_LEAVE" if is_full else "APPROVED_MORNING_LEAVE"
                existing.afternoon_status = "APPROVED_LEAVE" if is_full else "PENDING"
                existing.arrival_status = "ON_TIME"
                existing.attendance_day_value = 0.0 if is_full else 0.5
                existing.finalized_at = fin_time
                existing.status = "On Leave"
                existing.approved_leave_id = app_leave.id
                existing.working_minutes = 0
                finalized_leave += 1
                continue

            # Default: finalize existing record as ABSENT
            existing.morning_status = "ABSENT"
            existing.afternoon_status = "ABSENT"
            existing.final_status = "ABSENT"
            existing.arrival_status = None
            existing.attendance_day_value = 0.0
            existing.finalized_at = fin_time
            existing.status = "Absent"
            existing.working_minutes = 0
            existing.late_minutes = 0
            existing.overtime_minutes = 0
            finalized_absent += 1
            newly_affected_users.append(u)
            continue

        # No record exists for this employee and date: create new record
        fin_time = now.replace(tzinfo=None) if now.tzinfo else now
        if is_wo and is_h:
            hol_name = holiday_obj.holiday_name if holiday_obj else "Public Holiday"
            wo_h_rec = Attendance(
                employee_id=u.id,
                date=eval_date,
                final_status="HOLIDAY",
                morning_status="HOLIDAY",
                afternoon_status="WEEKLY_OFF",
                arrival_status="ON_TIME",
                attendance_day_value=0.0,
                finalized_at=fin_time,
                status=f"Holiday ({hol_name})",
                working_minutes=0,
            )
            db.add(wo_h_rec)
            finalized_holiday += 1
            continue

        if is_wo:
            wo_rec = Attendance(
                employee_id=u.id,
                date=eval_date,
                final_status="WEEKLY_OFF",
                morning_status="WEEKLY_OFF",
                afternoon_status="WEEKLY_OFF",
                arrival_status="ON_TIME",
                attendance_day_value=0.0,
                finalized_at=fin_time,
                status="Weekly Off",
                working_minutes=0,
            )
            db.add(wo_rec)
            finalized_weekly_off += 1
            continue

        if is_h:
            hol_name = holiday_obj.holiday_name if holiday_obj else "Public Holiday"
            h_rec = Attendance(
                employee_id=u.id,
                date=eval_date,
                final_status="HOLIDAY",
                morning_status="HOLIDAY",
                afternoon_status="HOLIDAY",
                arrival_status="ON_TIME",
                attendance_day_value=0.0,
                finalized_at=fin_time,
                status=f"Holiday ({hol_name})",
                working_minutes=0,
            )
            db.add(h_rec)
            finalized_holiday += 1
            continue

        app_leave = find_approved_leave_for_date(db, u.id, eval_date)
        if app_leave:
            is_full = (app_leave.half_day_session == "FULL_DAY" or not app_leave.half_day_session)
            l_rec = Attendance(
                employee_id=u.id,
                date=eval_date,
                final_status="FULL_DAY_LEAVE" if is_full else "HALF_DAY_LEAVE",
                morning_status="APPROVED_LEAVE" if is_full else "APPROVED_MORNING_LEAVE",
                afternoon_status="APPROVED_LEAVE" if is_full else "PENDING",
                arrival_status="ON_TIME",
                attendance_day_value=0.0 if is_full else 0.5,
                finalized_at=fin_time,
                status="On Leave",
                approved_leave_id=app_leave.id,
                working_minutes=0,
            )
            db.add(l_rec)
            finalized_leave += 1
            continue

        absent_rec = Attendance(
            employee_id=u.id,
            date=eval_date,
            check_in=None,
            check_out=None,
            morning_status="ABSENT",
            afternoon_status="ABSENT",
            final_status="ABSENT",
            arrival_status=None,
            attendance_day_value=0.0,
            finalized_at=fin_time,
            status="Absent",
            working_minutes=0,
            late_minutes=0,
            overtime_minutes=0,
        )
        db.add(absent_rec)
        finalized_absent += 1
        newly_affected_users.append(u)

        # Notify employee of absent status
        try:
            from .notification_service import create_notification
            create_notification(
                db,
                recipient_id=u.id,
                title="Attendance Status: Absent",
                body=f"You were marked absent for {eval_date.strftime('%d %b %Y')}. If you worked, please submit an Attendance Correction.",
                notification_type="ATTENDANCE_ABSENT",
                entity_type="attendance",
                entity_id=absent_rec.id,
                dedup_key=f"att_absent_{u.id}_{eval_date}",
                priority="normal",
                link_url="/employee/attendance",
            )
        except Exception:
            pass

    try:
        db.commit()
    except Exception as commit_err:
        db.rollback()
        return {"ok": False, "error": f"Database commit failed: {str(commit_err)}", "finalized_count": 0}

    # Recalculate burnout risk for affected users
    for u in newly_affected_users[:10]:
        try:
            predict_for_employee(db, u, persist=True)
        except Exception:
            pass

    return {
        "ok": True,
        "date": eval_date.isoformat(),
        "finalized_absent": finalized_absent,
        "finalized_holiday": finalized_holiday,
        "finalized_weekly_off": finalized_weekly_off,
        "finalized_leave": finalized_leave,
        "finalized_missing_checkout": finalized_missing_checkout,
        "unchanged": unchanged,
    }


def recover_missed_finalizations(db: Session, max_days_back: int = 14) -> dict:
    """
    Recovers missed finalizations after a server restart or downtime.
    Checks the past `max_days_back` days (excluding future dates and today if before cutoff).
    Finalizes unfinalized past dates idempotently without duplicate records.
    """
    settings = get_company_settings(db)
    now = get_current_time(settings.timezone)
    today = now.date()

    recovered_days = []
    total_finalized = 0

    users_count = db.query(User).filter(User.role.in_(["employee", "manager"])).count()
    if users_count == 0:
        return {"ok": True, "recovered_count": 0, "recovered_days": [], "message": "No active employees found"}

    for days_ago in range(1, max_days_back + 1):
        past_date = today - timedelta(days=days_ago)
        rec_count = db.query(Attendance).filter(Attendance.date == past_date).count()
        if rec_count < users_count:
            res = finalize_daily_attendance(db, target_date=past_date, force=True)
            recovered_days.append({
                "date": past_date.isoformat(),
                "details": res,
            })
            total_finalized += (
                res.get("finalized_absent", 0)
                + res.get("finalized_leave", 0)
                + res.get("finalized_holiday", 0)
                + res.get("finalized_weekly_off", 0)
            )

    # Check today if currently past 7:00 PM cutoff
    if now.time() >= time(19, 0):
        rec_count_today = db.query(Attendance).filter(Attendance.date == today).count()
        if rec_count_today < users_count:
            res = finalize_daily_attendance(db, target_date=today, force=False)
            recovered_days.append({
                "date": today.isoformat(),
                "details": res,
            })

    return {
        "ok": True,
        "recovered_count": len(recovered_days),
        "recovered_days": recovered_days,
        "total_records_processed": total_finalized,
    }


def create_attendance_correction_request(
    db: Session,
    employee: User,
    attendance_date: date,
    reason: str,
    requested_status: str = "FULL_DAY_PRESENT",
    requested_check_in: str | None = "09:00 AM",
    requested_check_out: str | None = "05:30 PM",
) -> dict:
    settings = get_company_settings(db)
    now = get_current_time(settings.timezone)
    today = now.date()

    if attendance_date > today:
        return {"error": "Cannot submit attendance correction for future dates."}
    if not reason or not reason.strip():
        return {"error": "A valid reason is required for attendance correction."}

    correction = AttendanceCorrection(
        employee_id=employee.id,
        attendance_date=attendance_date,
        requested_status=requested_status,
        requested_check_in=requested_check_in or "09:00 AM",
        requested_check_out=requested_check_out or "05:30 PM",
        reason=reason.strip(),
        status="Pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(correction)
    db.commit()
    db.refresh(correction)

    log_audit(
        db,
        actor=employee,
        action="ATTENDANCE_CORRECTION_REQUESTED",
        target_type="attendance_correction",
        target_id=correction.id,
        new_value={
            "date": attendance_date.isoformat(),
            "reason": reason.strip(),
            "requested_status": requested_status,
        },
    )

    return {
        "ok": True,
        "id": correction.id,
        "status": correction.status,
        "message": "Attendance correction request submitted for HR approval.",
    }


def get_attendance_corrections(
    db: Session,
    user: User,
    status_filter: str | None = None,
) -> list[dict]:
    query = db.query(AttendanceCorrection, User).join(User, AttendanceCorrection.employee_id == User.id)

    if user.role == "employee":
        query = query.filter(AttendanceCorrection.employee_id == user.id)
    elif user.role == "manager":
        query = query.filter((AttendanceCorrection.employee_id == user.id) | (User.department == user.department))

    if status_filter and status_filter.lower() != "all":
        query = query.filter(AttendanceCorrection.status.ilike(status_filter))

    rows = query.order_by(AttendanceCorrection.id.desc()).all()
    results = []
    for c, u in rows:
        results.append({
            "id": c.id,
            "employee_id": c.employee_id,
            "employee_name": u.name,
            "employee_code": u.employee_code,
            "department": u.department,
            "role": u.role,
            "attendance_date": c.attendance_date.isoformat(),
            "requested_status": c.requested_status,
            "requested_check_in": c.requested_check_in or "—",
            "requested_check_out": c.requested_check_out or "—",
            "reason": c.reason,
            "status": c.status,
            "reviewed_by_name": c.reviewed_by_name,
            "reviewed_at": c.reviewed_at.isoformat() if c.reviewed_at else None,
            "rejection_reason": c.rejection_reason,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return results


def approve_attendance_correction(db: Session, approver: User, correction_id: int) -> dict:
    if approver.role != "hr":
        return {"error": "Unauthorized: Only HR can approve attendance corrections."}

    correction = db.query(AttendanceCorrection).filter(AttendanceCorrection.id == correction_id).first()
    if not correction:
        return {"error": "Attendance correction request not found."}
    if correction.status != "Pending":
        return {"error": f"Request cannot be approved; current status is '{correction.status}'."}

    target_emp = db.query(User).filter(User.id == correction.employee_id).first()
    if not target_emp:
        return {"error": "Target employee not found."}

    att = db.query(Attendance).filter(
        Attendance.employee_id == correction.employee_id,
        Attendance.date == correction.attendance_date,
    ).first()

    old_status = att.final_status if att else "None"
    check_in_str = correction.requested_check_in or "09:00 AM"
    check_out_str = correction.requested_check_out or "05:30 PM"

    if not att:
        att = Attendance(
            employee_id=correction.employee_id,
            date=correction.attendance_date,
            check_in=check_in_str,
            check_out=check_out_str,
            morning_status="PRESENT",
            afternoon_status="PRESENT",
            final_status="FULL_DAY_PRESENT",
            arrival_status="ON_TIME",
            attendance_day_value=1.0,
            finalized_at=datetime.utcnow(),
            status="Present",
            working_minutes=510,
            overtime_minutes=0,
            late_minutes=0,
            created_at=datetime.utcnow(),
        )
        db.add(att)
    else:
        att.check_in = check_in_str
        att.check_out = check_out_str
        att.morning_status = "PRESENT"
        att.afternoon_status = "PRESENT"
        att.final_status = "FULL_DAY_PRESENT"
        att.arrival_status = "ON_TIME"
        att.attendance_day_value = 1.0
        att.finalized_at = datetime.utcnow()
        att.status = "Present"
        att.working_minutes = 510
        att.late_minutes = 0
        att.early_checkout_minutes = 0

    correction.status = "Approved"
    correction.reviewed_by_id = approver.id
    correction.reviewed_by_name = approver.name
    correction.reviewed_at = datetime.utcnow()
    correction.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(correction)
    db.refresh(att)

    log_audit(
        db,
        actor=approver,
        action="ATTENDANCE_CORRECTION_APPROVED",
        target_type="attendance",
        target_id=att.id,
        old_value={"status": old_status},
        new_value={"status": att.final_status, "corrected_by": approver.name},
    )

    from .notification_service import create_notification
    create_notification(
        db,
        recipient_id=correction.employee_id,
        title="Attendance Correction Approved",
        body=f"Your attendance correction for {correction.attendance_date} has been approved by HR. Status updated to {att.final_status}.",
        notification_type="ATTENDANCE_CORRECTION_APPROVED",
        entity_type="attendance",
        entity_id=att.id,
        priority="normal",
        link_url="/employee/attendance",
        dedup_key=f"att_corr_appr_{correction.id}",
    )

    pred = None
    try:
        from .burnout_service import recalculate_employee_burnout
        pred = recalculate_employee_burnout(db, correction.employee_id, trigger_source="attendance_correction_approved", actor=approver, persist=True)
    except Exception:
        pass

    return {
        "ok": True,
        "message": "Attendance correction approved successfully.",
        "correction_id": correction.id,
        "new_status": att.final_status,
        "prediction": pred,
    }


def reject_attendance_correction(db: Session, approver: User, correction_id: int, rejection_reason: str | None = None) -> dict:
    if approver.role != "hr":
        return {"error": "Unauthorized: Only HR can reject attendance corrections."}

    correction = db.query(AttendanceCorrection).filter(AttendanceCorrection.id == correction_id).first()
    if not correction:
        return {"error": "Attendance correction request not found."}
    if correction.status != "Pending":
        return {"error": f"Request cannot be rejected; current status is '{correction.status}'."}

    correction.status = "Rejected"
    correction.rejection_reason = rejection_reason or "Correction request rejected by HR."
    correction.reviewed_by_id = approver.id
    correction.reviewed_by_name = approver.name
    correction.reviewed_at = datetime.utcnow()
    correction.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(correction)

    log_audit(
        db,
        actor=approver,
        action="ATTENDANCE_CORRECTION_REJECTED",
        target_type="attendance_correction",
        target_id=correction.id,
        new_value={"rejection_reason": correction.rejection_reason},
    )

    from .notification_service import create_notification
    create_notification(
        db,
        recipient_id=correction.employee_id,
        title="Attendance Correction Rejected",
        body=f"Your attendance correction for {correction.attendance_date} was rejected: {correction.rejection_reason}",
        notification_type="ATTENDANCE_CORRECTION_REJECTED",
        entity_type="attendance",
        entity_id=correction.id,
        priority="high",
        link_url="/employee/attendance",
        dedup_key=f"att_corr_rej_{correction.id}",
    )

    return {
        "ok": True,
        "message": "Attendance correction request rejected.",
        "correction_id": correction.id,
        "status": "Rejected",
    }
