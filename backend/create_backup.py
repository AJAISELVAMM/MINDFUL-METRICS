import os
import json
from datetime import datetime, date
from app.database import SessionLocal, engine
from app.models import (
    User, CompanySettings, Department, Attendance, LeaveRequest, PermissionRequest,
    SurveyQuestion, Survey, PulseSurvey, Task, TaskUnblockRequest, Communication,
    Prediction, BurnoutFeatures, Notification, AuditLog, ModelVersion, Intervention,
    Holiday, AttendanceCorrection
)

def main():
    os.makedirs("backups", exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join("backups", f"backup_full_{ts}.json")

    db = SessionLocal()

    def serialize_obj(obj):
        d = {}
        for col in obj.__table__.columns:
            val = getattr(obj, col.name)
            if isinstance(val, (datetime, date)):
                d[col.name] = val.isoformat()
            else:
                d[col.name] = val
        return d

    data = {
        "created_at": datetime.utcnow().isoformat(),
        "database_host": engine.url.host,
        "database_name": engine.url.database,
        "users": [serialize_obj(o) for o in db.query(User).all()],
        "departments": [serialize_obj(o) for o in db.query(Department).all()],
        "attendance": [serialize_obj(o) for o in db.query(Attendance).all()],
        "leave_requests": [serialize_obj(o) for o in db.query(LeaveRequest).all()],
        "permission_requests": [serialize_obj(o) for o in db.query(PermissionRequest).all()],
        "tasks": [serialize_obj(o) for o in db.query(Task).all()],
        "task_unblock_requests": [serialize_obj(o) for o in db.query(TaskUnblockRequest).all()],
        "daily_surveys": [serialize_obj(o) for o in db.query(Survey).all()],
        "pulse_surveys": [serialize_obj(o) for o in db.query(PulseSurvey).all()],
        "burnout_predictions": [serialize_obj(o) for o in db.query(Prediction).all()],
        "burnout_features": [serialize_obj(o) for o in db.query(BurnoutFeatures).all()],
        "notifications": [serialize_obj(o) for o in db.query(Notification).all()],
        "audit_logs": [serialize_obj(o) for o in db.query(AuditLog).all()],
        "interventions": [serialize_obj(o) for o in db.query(Intervention).all()],
        "attendance_corrections": [serialize_obj(o) for o in db.query(AttendanceCorrection).all()],
        "holidays": [serialize_obj(o) for o in db.query(Holiday).all()],
        "company_settings": [serialize_obj(o) for o in db.query(CompanySettings).all()],
    }

    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    file_size = os.path.getsize(backup_path)
    print(f"Backup created successfully: {backup_path} ({file_size} bytes)")
    print(f"Backed up {len(data['users'])} users, {len(data['attendance'])} attendance records, {len(data['tasks'])} tasks, {len(data['leave_requests'])} leaves.")
    db.close()

if __name__ == "__main__":
    main()
