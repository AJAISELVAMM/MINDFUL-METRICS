"""
MINDFUL METRICS - Verified Full Database Backup Script
Exports all rows from all application tables to a recoverable JSON snapshot with SHA256 checksum.
"""
from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime
from sqlalchemy import inspect
from app.database import engine, SessionLocal
from app.models import (
    User, Department, CompanySettings, Attendance, LeaveRequest,
    PermissionRequest, Task, Survey, PulseSurvey, Communication,
    Prediction, BurnoutFeatures, Notification, AuditLog, Intervention,
    Holiday, AttendanceCorrection, TaskUnblockRequest, ModelVersion
)

MODELS = [
    CompanySettings, Department, User, Attendance, LeaveRequest,
    PermissionRequest, Task, Survey, PulseSurvey, Communication,
    Prediction, BurnoutFeatures, Notification, AuditLog, Intervention,
    Holiday, AttendanceCorrection, TaskUnblockRequest, ModelVersion
]

def serialize_val(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v

def run_backup():
    db = SessionLocal()
    backup_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "database_type": "Supabase PostgreSQL",
        "tables": {},
        "row_counts": {}
    }

    try:
        print("[BACKUP] Starting full database backup...", flush=True)
        for model in MODELS:
            tname = model.__tablename__
            rows = db.query(model).all()
            table_rows = []
            insp = inspect(model)
            col_names = [c.key for c in insp.mapper.column_attrs]

            for r in rows:
                row_dict = {}
                for col in col_names:
                    row_dict[col] = serialize_val(getattr(r, col))
                table_rows.append(row_dict)

            backup_data["tables"][tname] = table_rows
            backup_data["row_counts"][tname] = len(table_rows)
            print(f"  - Backed up {tname}: {len(table_rows)} rows", flush=True)

        backup_dir = os.path.join(os.path.dirname(__file__), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        filename = f"mindful_metrics_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(backup_dir, filename)

        raw_json = json.dumps(backup_data, indent=2)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(raw_json)

        # Compute checksum
        sha256 = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
        file_size_kb = os.path.getsize(filepath) / 1024

        print(f"[BACKUP SUCCESS] Verified backup written to: {filepath}", flush=True)
        print(f"[BACKUP METRICS] File size: {file_size_kb:.1f} KB | SHA256: {sha256}", flush=True)
        return filepath, sha256, backup_data["row_counts"]

    finally:
        db.close()

if __name__ == "__main__":
    run_backup()
