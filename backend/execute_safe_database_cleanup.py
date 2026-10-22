"""
MINDFUL METRICS - Safe Confirmed Database Cleanup
Removes non-Gmail accounts and their exclusively associated records in a single controlled transaction.
Preserves all Gmail accounts and shared reference data.
"""
from app.database import SessionLocal
from app.models import (
    User, Attendance, LeaveRequest, PermissionRequest, Task, Survey,
    PulseSurvey, Communication, Prediction, BurnoutFeatures, Notification,
    AuditLog, Intervention, AttendanceCorrection, TaskUnblockRequest
)

def execute_cleanup():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        gmail_users = [u for u in users if (u.email or "").strip().lower().endswith("@gmail.com")]
        non_gmail_users = [u for u in users if not (u.email or "").strip().lower().endswith("@gmail.com")]

        print(f"[CLEANUP] Starting confirmed deletion of {len(non_gmail_users)} non-Gmail accounts...")
        non_gmail_ids = [u.id for u in non_gmail_users]

        if not non_gmail_ids:
            print("[CLEANUP] No non-Gmail accounts found. Database is already clean.")
            return

        for u in non_gmail_users:
            print(f"  - Removing User ID {u.id}: '{u.name}' ({u.email})")

        # 1. Nullify foreign key references from Gmail records to non-Gmail users
        # Users manager_id
        db.query(User).filter(User.manager_id.in_(non_gmail_ids)).update({User.manager_id: None}, synchronize_session=False)

        # Tasks assigned_by_id for Gmail employees
        db.query(Task).filter(Task.assigned_by_id.in_(non_gmail_ids), ~Task.employee_id.in_(non_gmail_ids)).update({Task.assigned_by_id: None}, synchronize_session=False)

        # Attendance corrections reviewed_by_id for Gmail employees
        db.query(AttendanceCorrection).filter(AttendanceCorrection.reviewed_by_id.in_(non_gmail_ids), ~AttendanceCorrection.employee_id.in_(non_gmail_ids)).update({AttendanceCorrection.reviewed_by_id: None}, synchronize_session=False)

        # Interventions created_by_id for Gmail employees
        db.query(Intervention).filter(Intervention.created_by_id.in_(non_gmail_ids), ~Intervention.employee_id.in_(non_gmail_ids)).update({Intervention.created_by_id: None}, synchronize_session=False)

        # Task unblock requests reviewed_by_id for Gmail employees
        db.query(TaskUnblockRequest).filter(TaskUnblockRequest.reviewed_by_id.in_(non_gmail_ids), ~TaskUnblockRequest.requester_id.in_(non_gmail_ids)).update({TaskUnblockRequest.reviewed_by_id: None}, synchronize_session=False)

        # Audit logs actor_id
        db.query(AuditLog).filter(AuditLog.actor_id.in_(non_gmail_ids)).update({AuditLog.actor_id: None}, synchronize_session=False)

        # 2. Delete records owned exclusively by non-Gmail users
        db.query(AttendanceCorrection).filter(AttendanceCorrection.employee_id.in_(non_gmail_ids)).delete(synchronize_session=False)
        db.query(TaskUnblockRequest).filter(TaskUnblockRequest.requester_id.in_(non_gmail_ids)).delete(synchronize_session=False)
        db.query(Intervention).filter(Intervention.employee_id.in_(non_gmail_ids)).delete(synchronize_session=False)
        db.query(Notification).filter(Notification.employee_id.in_(non_gmail_ids)).delete(synchronize_session=False)
        db.query(BurnoutFeatures).filter(BurnoutFeatures.employee_id.in_(non_gmail_ids)).delete(synchronize_session=False)
        db.query(Prediction).filter(Prediction.employee_id.in_(non_gmail_ids)).delete(synchronize_session=False)
        db.query(Communication).filter(Communication.employee_id.in_(non_gmail_ids)).delete(synchronize_session=False)
        db.query(Survey).filter(Survey.employee_id.in_(non_gmail_ids)).delete(synchronize_session=False)
        db.query(PulseSurvey).filter(PulseSurvey.employee_id.in_(non_gmail_ids)).delete(synchronize_session=False)
        db.query(Task).filter(Task.employee_id.in_(non_gmail_ids)).delete(synchronize_session=False)
        db.query(PermissionRequest).filter(PermissionRequest.employee_id.in_(non_gmail_ids)).delete(synchronize_session=False)
        db.query(LeaveRequest).filter(LeaveRequest.employee_id.in_(non_gmail_ids)).delete(synchronize_session=False)
        db.query(Attendance).filter(Attendance.employee_id.in_(non_gmail_ids)).delete(synchronize_session=False)

        # 3. Delete non-Gmail users themselves
        deleted_count = db.query(User).filter(User.id.in_(non_gmail_ids)).delete(synchronize_session=False)
        db.commit()

        print(f"[CLEANUP SUCCESS] Successfully removed {deleted_count} non-Gmail accounts.")

        # Post-cleanup verification
        retained = db.query(User).all()
        print(f"[VERIFICATION] Retained User Count: {len(retained)}")
        assert len(retained) == 45, f"Expected 45 retained users, got {len(retained)}"
        for u in retained:
            assert (u.email or "").strip().lower().endswith("@gmail.com"), f"Found unexpected non-Gmail user: {u.email}"
        print("[VERIFICATION] 100% of retained users have verified normalized @gmail.com emails!")

    except Exception as e:
        db.rollback()
        print(f"[CLEANUP ERROR] Transaction rolled back: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    execute_cleanup()
