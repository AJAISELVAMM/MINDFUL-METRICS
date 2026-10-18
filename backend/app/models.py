from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Text, ForeignKey, UniqueConstraint, JSON, Boolean
from .database import Base


class CompanySettings(Base):
    __tablename__ = "company_settings"
    id = Column(Integer, primary_key=True)
    work_start_time = Column(String(10), default="09:00")
    checkin_grace_time = Column(String(10), default="09:30")
    afternoon_start_time = Column(String(10), default="13:00")
    early_checkout_threshold = Column(String(10), default="17:00")
    work_end_time = Column(String(10), default="17:30")
    timezone = Column(String(50), default="Asia/Kolkata")
    survey_start_time = Column(String(10), default="11:30")
    survey_end_time = Column(String(10), default="15:00")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(180), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(20), nullable=False)  # "employee", "manager", "hr"
    department = Column(String(80), default="Engineering")
    employee_code = Column(String(20), unique=True)
    manager_name = Column(String(120), default="")
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    phone = Column(String(40), default="+91 98765 43210")
    avatar = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True, nullable=False)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("employee_id", "date", name="uq_att_day"),)
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    check_in = Column(String(20), nullable=True)
    check_out = Column(String(20), nullable=True)
    check_in_at = Column(DateTime, nullable=True)
    check_out_at = Column(DateTime, nullable=True)
    morning_status = Column(String(40), default="PENDING")
    afternoon_status = Column(String(40), default="PENDING")
    final_status = Column(String(50), default="WORKING")
    working_minutes = Column(Integer, default=0)
    overtime_minutes = Column(Integer, default=0)
    late_minutes = Column(Integer, default=0)
    early_checkout_minutes = Column(Integer, default=0)
    approved_leave_id = Column(Integer, nullable=True)
    approved_permission_id = Column(Integer, nullable=True)
    arrival_status = Column(String(20), default="ON_TIME")
    attendance_day_value = Column(Float, default=1.0)
    finalized_at = Column(DateTime, nullable=True)
    status = Column(String(40), default="Working")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    employee_name = Column(String(120))
    department = Column(String(80), default="Engineering")
    role = Column(String(20), default="employee")
    type = Column(String(40), default="Casual Leave")
    leave_type = Column(String(40), default="Casual Leave")
    date = Column(String(80))
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    duration = Column(String(40), default="1 day")
    half_day_session = Column(String(30), default="FULL_DAY")  # FULL_DAY, MORNING_HALF_DAY, AFTERNOON_HALF_DAY
    reason = Column(Text)
    status = Column(String(20), default="Pending")  # Pending, Approved, Rejected, Cancelled
    manager_status = Column(String(20), default="Pending")
    approved_by = Column(String(120), nullable=True)
    approver_name = Column(String(120), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PermissionRequest(Base):
    __tablename__ = "permission_requests"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    employee_name = Column(String(120))
    department = Column(String(80), default="Engineering")
    role = Column(String(20), default="employee")
    date = Column(Date, nullable=False)
    requested_checkout_time = Column(String(30), nullable=False)  # e.g. "04:30 PM"
    reason = Column(Text)
    status = Column(String(20), default="Pending")  # Pending, Approved, Rejected, Cancelled
    approved_by = Column(String(120), nullable=True)
    approver_name = Column(String(120), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SurveyQuestion(Base):
    __tablename__ = "survey_questions"
    id = Column(Integer, primary_key=True)
    category = Column(String(40), default="wellbeing")  # wellbeing, work, manager, hr
    role_target = Column(String(20), default="all")  # employee, manager, hr, all
    question_key = Column(String(40), nullable=False)
    question_text = Column(Text, nullable=False)
    low_label = Column(String(40), default="Low")
    high_label = Column(String(40), default="High")
    is_active = Column(Integer, default=1)


class Survey(Base):
    __tablename__ = "daily_surveys"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    survey_type = Column(String(20), default="daily")  # daily, morning, evening, pulse, manager, hr
    role = Column(String(20), default="employee")
    answers = Column(JSON)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PulseSurvey(Base):
    __tablename__ = "pulse_surveys"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    workload_response = Column(String(40), nullable=False)  # "Low", "Moderate", "High", "Very High"
    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_by_name = Column(String(120), nullable=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(20), default="Medium")
    deadline = Column(String(40))
    start_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    status = Column(String(30), default="Pending")  # Not Started, In Progress, Almost Completed, Completed, Overdue, Blocked
    completion_percentage = Column(Integer, default=0)
    difficulty = Column(Integer, default=3)
    work_update = Column(Text, nullable=True)
    blocked_reason = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verification_status = Column(String(40), default="None")  # None, Awaiting Verification, Verified, Changes Requested
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verification_notes = Column(Text, nullable=True)
    missed_deadline_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaskUnblockRequest(Base):
    __tablename__ = "task_unblock_requests"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    requester_role = Column(String(20), default="employee")
    original_deadline = Column(String(40), nullable=True)
    requested_new_deadline = Column(String(40), nullable=False)
    requested_due_date = Column(Date, nullable=True)
    blocking_reason = Column(Text, nullable=True)
    extension_reason = Column(Text, nullable=False)
    work_completed = Column(Text, nullable=False)
    remaining_work = Column(Text, nullable=False)
    supporting_notes = Column(Text, nullable=True)
    status = Column(String(40), default="Pending HR Review")  # Pending HR Review, More Information Required, Approved, Rejected
    clarification_requested = Column(Text, nullable=True)
    clarification_requested_at = Column(DateTime, nullable=True)
    clarification_response = Column(Text, nullable=True)
    clarification_responded_at = Column(DateTime, nullable=True)
    decision_reason = Column(Text, nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Communication(Base):
    __tablename__ = "communications"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text)
    source = Column(String(40), default="reflection")
    sentiment_score = Column(Float, default=0)
    stress_keyword_score = Column(Float, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Prediction(Base):
    __tablename__ = "burnout_predictions"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    prediction_date = Column(DateTime, default=datetime.utcnow)
    burnout_score = Column(Float)
    risk_level = Column(String(20))
    confidence = Column(Float)
    model_version = Column(String(20), default="rf-v1")
    top_factors = Column(JSON)
    recommendations = Column(JSON, nullable=True)
    probabilities = Column(JSON, nullable=True)


class BurnoutFeatures(Base):
    __tablename__ = "burnout_features"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    features = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(String(60), default="GENERAL")
    title = Column(String(160), nullable=False)
    body = Column(Text, nullable=False)
    time = Column(String(40), default="Now")
    unread = Column(Integer, default=1)  # 1 = unread, 0 = read (preserved for backwards compatibility)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    is_archived = Column(Boolean, default=False)
    archived_at = Column(DateTime, nullable=True)
    entity_type = Column(String(40), nullable=True)  # task, leave, attendance, unblock_request, intervention, burnout
    entity_id = Column(String(60), nullable=True)
    dedup_key = Column(String(160), nullable=True)
    group_key = Column(String(100), nullable=True)
    priority = Column(String(20), default="normal")  # low, normal, high, critical
    link_url = Column(String(160), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_name = Column(String(120), nullable=True)
    actor_role = Column(String(20), nullable=True)
    action = Column(String(60), nullable=False)
    target_type = Column(String(60), nullable=True)
    target_id = Column(String(60), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id = Column(Integer, primary_key=True)
    name = Column(String(60), nullable=False)
    version = Column(String(40), nullable=False)
    algorithm = Column(String(60), nullable=False)
    metrics = Column(JSON, nullable=True)
    is_active = Column(Integer, default=1)
    trained_at = Column(DateTime, default=datetime.utcnow)


class Intervention(Base):
    __tablename__ = "interventions"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    employee_name = Column(String(120), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = Column(String(120), nullable=True)
    risk_level = Column(String(20), default="High")  # Low, Moderate, High
    trigger_reason = Column(Text, nullable=True)
    intervention_type = Column(String(80), default="Workload Review")
    recommendation = Column(Text, nullable=True)
    status = Column(String(30), default="OPEN")  # OPEN, IN_PROGRESS, RESOLVED
    follow_up_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Holiday(Base):
    __tablename__ = "holidays"
    __table_args__ = (
        UniqueConstraint("holiday_date", "holiday_name", name="uq_holiday_date_name"),
    )
    id = Column(Integer, primary_key=True)
    holiday_date = Column(Date, nullable=False, index=True)
    holiday_name = Column(String(180), nullable=False)
    holiday_type = Column(String(50), default="Public Holiday")  # "Public Holiday", "Bank Holiday", etc.
    calendar_year = Column(Integer, default=2026, index=True)
    source_name = Column(String(180), default="Tamil Nadu Government Gazette Public Holidays 2026")
    source_reference = Column(String(180), default="G.O.(Ms.) No. 708, Public (Miscellaneous) Department, dated 11.11.2025")
    source_verified = Column(Integer, default=1)  # 1 for True, 0 for False
    applicability = Column(String(50), default="all")  # "all", "company", "bank_only"
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AttendanceCorrection(Base):
    __tablename__ = "attendance_corrections"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    attendance_date = Column(Date, nullable=False, index=True)
    requested_status = Column(String(50), default="FULL_DAY_PRESENT")
    requested_check_in = Column(String(20), nullable=True)
    requested_check_out = Column(String(20), nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(String(20), default="Pending")  # "Pending", "Approved", "Rejected"
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by_name = Column(String(120), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

