"""
MINDFUL METRICS - Database Performance Optimization: High-Impact Indexes
Creates targeted B-tree indexes for all frequently filtered foreign keys,
timestamps, and status columns across PostgreSQL tables.
"""
from __future__ import annotations
from sqlalchemy import text
from app.database import engine

INDEXES = [
    # Tasks
    ("idx_tasks_assigned_by_id", "CREATE INDEX IF NOT EXISTS idx_tasks_assigned_by_id ON tasks (assigned_by_id)"),
    ("idx_tasks_verified_by_id", "CREATE INDEX IF NOT EXISTS idx_tasks_verified_by_id ON tasks (verified_by_id)"),
    ("idx_tasks_completed_by_id", "CREATE INDEX IF NOT EXISTS idx_tasks_completed_by_id ON tasks (completed_by_id)"),
    ("idx_tasks_verification_status", "CREATE INDEX IF NOT EXISTS idx_tasks_verification_status ON tasks (verification_status)"),
    ("idx_tasks_emp_status", "CREATE INDEX IF NOT EXISTS idx_tasks_emp_status ON tasks (employee_id, status)"),

    # Surveys & ML Features
    ("idx_daily_surveys_employee_id", "CREATE INDEX IF NOT EXISTS idx_daily_surveys_employee_id ON daily_surveys (employee_id)"),
    ("idx_daily_surveys_date", "CREATE INDEX IF NOT EXISTS idx_daily_surveys_date ON daily_surveys (date)"),
    ("idx_pulse_surveys_employee_id", "CREATE INDEX IF NOT EXISTS idx_pulse_surveys_employee_id ON pulse_surveys (employee_id)"),
    ("idx_burnout_features_employee_id", "CREATE INDEX IF NOT EXISTS idx_burnout_features_employee_id ON burnout_features (employee_id)"),
    ("idx_burnout_predictions_emp_id_id", "CREATE INDEX IF NOT EXISTS idx_burnout_predictions_emp_id_id ON burnout_predictions (employee_id, id DESC)"),

    # Communications, Notifications, Audits
    ("idx_communications_employee_id", "CREATE INDEX IF NOT EXISTS idx_communications_employee_id ON communications (employee_id)"),
    ("idx_notifications_employee_id", "CREATE INDEX IF NOT EXISTS idx_notifications_employee_id ON notifications (employee_id)"),
    ("idx_audit_logs_actor_id", "CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_id ON audit_logs (actor_id)"),
    ("idx_interventions_employee_id", "CREATE INDEX IF NOT EXISTS idx_interventions_employee_id ON interventions (employee_id)"),
    ("idx_interventions_created_by_id", "CREATE INDEX IF NOT EXISTS idx_interventions_created_by_id ON interventions (created_by_id)"),

    # Requests & Verification Queues
    ("idx_task_unblock_requests_task_id", "CREATE INDEX IF NOT EXISTS idx_task_unblock_requests_task_id ON task_unblock_requests (task_id)"),
    ("idx_task_unblock_requests_requester_id", "CREATE INDEX IF NOT EXISTS idx_task_unblock_requests_requester_id ON task_unblock_requests (requester_id)"),
    ("idx_task_unblock_requests_status", "CREATE INDEX IF NOT EXISTS idx_task_unblock_requests_status ON task_unblock_requests (status)"),
    ("idx_attendance_corrections_employee_id", "CREATE INDEX IF NOT EXISTS idx_attendance_corrections_employee_id ON attendance_corrections (employee_id)"),
    ("idx_attendance_corrections_status", "CREATE INDEX IF NOT EXISTS idx_attendance_corrections_status ON attendance_corrections (status)"),
    ("idx_leave_requests_status", "CREATE INDEX IF NOT EXISTS idx_leave_requests_status ON leave_requests (status)"),
    ("idx_permission_requests_status", "CREATE INDEX IF NOT EXISTS idx_permission_requests_status ON permission_requests (status)"),
    ("idx_attendance_emp_date", "CREATE INDEX IF NOT EXISTS idx_attendance_emp_date ON attendance (employee_id, date DESC)"),
]

def apply_indexes():
    print("[INDEXES] Applying performance indexes to PostgreSQL...", flush=True)
    with engine.begin() as conn:
        for name, ddl in INDEXES:
            conn.execute(text(ddl))
            print(f"  [OK] {name}", flush=True)
    print("[INDEXES SUCCESS] All performance indexes verified and active.", flush=True)

if __name__ == "__main__":
    apply_indexes()
