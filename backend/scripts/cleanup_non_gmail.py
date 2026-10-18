from __future__ import annotations
import logging
from app.database import SessionLocal
from app.models import (
    User, Department, Attendance, LeaveRequest, PermissionRequest, Survey, PulseSurvey, Task,
    TaskUnblockRequest, Communication, Prediction, BurnoutFeatures, Notification,
    AuditLog, Intervention, AttendanceCorrection
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def execute_cleanup():
    db = SessionLocal()
    try:
        all_users = db.query(User).all()
        gmail_users = [u for u in all_users if (u.email or "").strip().lower().endswith("@gmail.com")]
        non_gmail_users = [u for u in all_users if not (u.email or "").strip().lower().endswith("@gmail.com")]

        logger.info(f"Total Users: {len(all_users)}")
        logger.info(f"Retained Gmail Users: {len(gmail_users)}")
        logger.info(f"Non-Gmail Users to Delete: {len(non_gmail_users)}")

        if not non_gmail_users:
            logger.info("No non-Gmail users found to clean up. Exiting.")
            return

        non_gmail_ids = [u.id for u in non_gmail_users]
        str_non_gmail_ids = [str(uid) for uid in non_gmail_ids]

        logger.info(f"Target Non-Gmail User IDs: {non_gmail_ids}")

        # Execute all in a transaction
        logger.info("Starting atomic transaction for cleanup...")

        # 0. Clear Department.manager_id if pointing to any non-gmail user
        db.query(Department).filter(Department.manager_id.in_(non_gmail_ids)).update({"manager_id": None}, synchronize_session=False)

        # 1. Attendance
        del_att = db.query(Attendance).filter(Attendance.employee_id.in_(non_gmail_ids)).delete(synchronize_session=False)
        logger.info(f"Deleted {del_att} Attendance records")

        # 2. TaskUnblockRequest
        del_unblock = db.query(TaskUnblockRequest).filter(
            (TaskUnblockRequest.requester_id.in_(non_gmail_ids)) | 
            (TaskUnblockRequest.reviewed_by_id.in_(non_gmail_ids))
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {del_unblock} TaskUnblockRequest records")

        # 3. Tasks
        del_tasks = db.query(Task).filter(
            (Task.employee_id.in_(non_gmail_ids)) | 
            (Task.assigned_by_id.in_(non_gmail_ids)) | 
            (Task.completed_by_id.in_(non_gmail_ids)) | 
            (Task.verified_by_id.in_(non_gmail_ids))
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {del_tasks} Task records")

        # 4. Daily Surveys & Pulse Surveys
        del_surv = db.query(Survey).filter(Survey.employee_id.in_(non_gmail_ids)).delete(synchronize_session=False)
        del_pulse = db.query(PulseSurvey).filter(PulseSurvey.employee_id.in_(non_gmail_ids)).delete(synchronize_session=False)
        logger.info(f"Deleted {del_surv} Survey and {del_pulse} PulseSurvey records")

        # 5. Predictions & BurnoutFeatures
        del_pred = db.query(Prediction).filter(Prediction.employee_id.in_(non_gmail_ids)).delete(synchronize_session=False)
        del_feat = db.query(BurnoutFeatures).filter(BurnoutFeatures.employee_id.in_(non_gmail_ids)).delete(synchronize_session=False)
        logger.info(f"Deleted {del_pred} Prediction and {del_feat} BurnoutFeatures records")

        # 6. Notifications
        del_notif = db.query(Notification).filter(Notification.employee_id.in_(non_gmail_ids)).delete(synchronize_session=False)
        logger.info(f"Deleted {del_notif} Notification records")

        # 7. AuditLog
        del_audit = db.query(AuditLog).filter(
            (AuditLog.actor_id.in_(non_gmail_ids)) | 
            ((AuditLog.target_type == "user") & (AuditLog.target_id.in_(str_non_gmail_ids)))
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {del_audit} AuditLog records")

        # 8. Interventions & Corrections
        del_interv = db.query(Intervention).filter(
            (Intervention.employee_id.in_(non_gmail_ids)) | 
            (Intervention.created_by_id.in_(non_gmail_ids))
        ).delete(synchronize_session=False)
        del_corr = db.query(AttendanceCorrection).filter(
            (AttendanceCorrection.employee_id.in_(non_gmail_ids)) | 
            (AttendanceCorrection.reviewed_by_id.in_(non_gmail_ids))
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {del_interv} Intervention and {del_corr} AttendanceCorrection records")

        # 9. Permission & Leave Requests
        del_perm = db.query(PermissionRequest).filter(
            PermissionRequest.employee_id.in_(non_gmail_ids)
        ).delete(synchronize_session=False)
        del_leave = db.query(LeaveRequest).filter(
            LeaveRequest.employee_id.in_(non_gmail_ids)
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {del_perm} PermissionRequest and {del_leave} LeaveRequest records")

        # 10. Communication
        del_comm = db.query(Communication).filter(
            Communication.employee_id.in_(non_gmail_ids)
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {del_comm} Communication records")

        # 11. Clear self-referencing and cross-referencing manager_id
        db.query(User).filter(User.manager_id.in_(non_gmail_ids)).update({"manager_id": None}, synchronize_session=False)
        db.query(User).filter(User.id.in_(non_gmail_ids)).update({"manager_id": None}, synchronize_session=False)

        # 12. Finally, delete the Users
        del_users = db.query(User).filter(User.id.in_(non_gmail_ids)).delete(synchronize_session=False)
        logger.info(f"Deleted {del_users} non-Gmail User accounts")

        # Commit transaction
        db.commit()
        logger.info("Successfully committed transaction.")

        # Verification
        remaining_all = db.query(User).all()
        remaining_non_gmail = [u for u in remaining_all if not (u.email or "").strip().lower().endswith("@gmail.com")]
        logger.info(f"Verification: Total Users Remaining = {len(remaining_all)}")
        logger.info(f"Verification: Non-Gmail Users Remaining = {len(remaining_non_gmail)}")
        assert len(remaining_non_gmail) == 0, "Error: non-Gmail users still remain!"
        assert len(remaining_all) == 45, f"Expected 45 Gmail users, found {len(remaining_all)}"
        logger.info("ALL VERIFICATIONS PASSED: 100% of remaining users are valid @gmail.com accounts!")

    except Exception as e:
        db.rollback()
        logger.error(f"Cleanup failed, transaction rolled back: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    execute_cleanup()
