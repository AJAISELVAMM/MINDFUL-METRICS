"""
MINDFUL METRICS - Safe Transactional Database Cleanup Script
Removes non-Gmail test/seed accounts and their exclusively associated records.
Performs pre-checks and executes within a single database transaction.
"""
from __future__ import annotations
import sys
from app.database import SessionLocal
from app.models import (
    User, Department, CompanySettings, Attendance, LeaveRequest,
    PermissionRequest, Task, Survey, PulseSurvey, Communication,
    Prediction, BurnoutFeatures, Notification, AuditLog, Intervention,
    AttendanceCorrection, TaskUnblockRequest
)

def execute_cleanup(dry_run: bool = True):
    db = SessionLocal()
    try:
        # 1. Fresh eligibility check
        all_users = db.query(User).all()
        to_delete = []
        to_retain = []

        for u in all_users:
            email_clean = (u.email or "").strip().lower()
            if email_clean.endswith("@gmail.com"):
                to_retain.append(u)
            else:
                to_delete.append(u)

        delete_ids = [u.id for u in to_delete]
        retain_ids = [u.id for u in to_retain]

        print(f"[AUDIT] Discovered {len(all_users)} total accounts.")
        print(f"[AUDIT] Retaining {len(to_retain)} @gmail.com accounts.")
        print(f"[AUDIT] Target for removal: {len(to_delete)} non-gmail accounts: {delete_ids}")

        if not to_delete:
            print("[INFO] No non-gmail accounts found. Database is already clean.")
            return

        # 2. Safety check: ensure no retained user is managed by a user to be deleted
        dangling_subordinates = db.query(User).filter(User.manager_id.in_(delete_ids), User.id.in_(retain_ids)).count()
        if dangling_subordinates > 0:
            raise RuntimeError(f"ABORT: {dangling_subordinates} retained user(s) have manager_id in deletion list!")

        # 3. Safety check: ensure no department is managed by a user to be deleted
        dangling_depts = db.query(Department).filter(Department.manager_id.in_(delete_ids)).count()
        if dangling_depts > 0:
            raise RuntimeError(f"ABORT: {dangling_depts} department(s) have manager_id in deletion list!")

        # 4. Safety check: ensure no tasks assigned to retained users were assigned by users to be deleted
        dangling_tasks = db.query(Task).filter(Task.assigned_by_id.in_(delete_ids), Task.employee_id.in_(retain_ids)).count()
        if dangling_tasks > 0:
            raise RuntimeError(f"ABORT: {dangling_tasks} tasks assigned to retained users depend on accounts to be deleted!")

        print("[SAFETY] Pre-checks passed: zero shared conflicts detected.")

        if dry_run:
            print("[DRY RUN] Simulating deletion in dry-run mode (no changes committed)...")

        # Start transactional deletion
        # 1. Child tables of tasks
        task_ids_to_delete = [t.id for t in db.query(Task.id).filter(Task.employee_id.in_(delete_ids) | Task.assigned_by_id.in_(delete_ids)).all()]
        
        del_unblock = db.query(TaskUnblockRequest).filter(
            TaskUnblockRequest.requester_id.in_(delete_ids) |
            TaskUnblockRequest.reviewed_by_id.in_(delete_ids) |
            TaskUnblockRequest.task_id.in_(task_ids_to_delete)
        ).delete(synchronize_session=False)

        del_tasks = db.query(Task).filter(
            Task.employee_id.in_(delete_ids) |
            Task.assigned_by_id.in_(delete_ids) |
            Task.completed_by_id.in_(delete_ids) |
            Task.verified_by_id.in_(delete_ids)
        ).delete(synchronize_session=False)

        del_att_corr = db.query(AttendanceCorrection).filter(
            AttendanceCorrection.employee_id.in_(delete_ids) |
            AttendanceCorrection.reviewed_by_id.in_(delete_ids)
        ).delete(synchronize_session=False)

        del_att = db.query(Attendance).filter(Attendance.employee_id.in_(delete_ids)).delete(synchronize_session=False)
        del_leave = db.query(LeaveRequest).filter(LeaveRequest.employee_id.in_(delete_ids)).delete(synchronize_session=False)
        del_perm = db.query(PermissionRequest).filter(PermissionRequest.employee_id.in_(delete_ids)).delete(synchronize_session=False)
        del_surveys = db.query(Survey).filter(Survey.employee_id.in_(delete_ids)).delete(synchronize_session=False)
        del_pulse = db.query(PulseSurvey).filter(PulseSurvey.employee_id.in_(delete_ids)).delete(synchronize_session=False)
        del_feats = db.query(BurnoutFeatures).filter(BurnoutFeatures.employee_id.in_(delete_ids)).delete(synchronize_session=False)
        del_preds = db.query(Prediction).filter(Prediction.employee_id.in_(delete_ids)).delete(synchronize_session=False)
        del_comms = db.query(Communication).filter(Communication.employee_id.in_(delete_ids)).delete(synchronize_session=False)
        del_notifs = db.query(Notification).filter(Notification.employee_id.in_(delete_ids)).delete(synchronize_session=False)
        del_audit = db.query(AuditLog).filter(AuditLog.actor_id.in_(delete_ids)).delete(synchronize_session=False)
        del_interventions = db.query(Intervention).filter(Intervention.employee_id.in_(delete_ids) | Intervention.created_by_id.in_(delete_ids)).delete(synchronize_session=False)

        # Clear any self-referential manager_ids among users to be deleted
        db.query(User).filter(User.id.in_(delete_ids)).update({"manager_id": None}, synchronize_session=False)

        # Delete users
        del_users = db.query(User).filter(User.id.in_(delete_ids)).delete(synchronize_session=False)

        print(f"[RECORDS REMOVED]")
        print(f"  - task_unblock_requests: {del_unblock}")
        print(f"  - tasks:                 {del_tasks}")
        print(f"  - attendance_corrections:{del_att_corr}")
        print(f"  - attendance:            {del_att}")
        print(f"  - leave_requests:        {del_leave}")
        print(f"  - permission_requests:   {del_perm}")
        print(f"  - daily_surveys:         {del_surveys}")
        print(f"  - pulse_surveys:         {del_pulse}")
        print(f"  - burnout_features:      {del_feats}")
        print(f"  - burnout_predictions:   {del_preds}")
        print(f"  - communications:        {del_comms}")
        print(f"  - notifications:         {del_notifs}")
        print(f"  - audit_logs:            {del_audit}")
        print(f"  - interventions:         {del_interventions}")
        print(f"  - users:                 {del_users}")

        if dry_run:
            db.rollback()
            print("[DRY RUN COMPLETE] Transaction rolled back cleanly. No changes were committed.")
        else:
            db.commit()
            print("[SUCCESS] Transaction committed successfully to database.")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Transaction rolled back due to error: {e}", file=sys.stderr)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    is_dry = "--commit" not in sys.argv
    execute_cleanup(dry_run=is_dry)
