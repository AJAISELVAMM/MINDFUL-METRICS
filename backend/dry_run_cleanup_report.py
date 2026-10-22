"""
MINDFUL METRICS - Staged Database Cleanup Dry-Run & Audit
Computes exact counts for Gmail accounts to retain vs non-Gmail accounts to remove,
audits all foreign key and relational tables, and prints a structured dry-run report.
NO MUTATIONS / DELETIONS ARE PERFORMED.
"""
import re
from datetime import datetime
from sqlalchemy import inspect
from app.database import SessionLocal
from app.models import (
    User, Department, CompanySettings, Attendance, LeaveRequest,
    PermissionRequest, Task, Survey, PulseSurvey, Communication,
    Prediction, BurnoutFeatures, Notification, AuditLog, Intervention,
    Holiday, AttendanceCorrection, TaskUnblockRequest, ModelVersion
)

def run_dry_run():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        total_users = len(users)
        
        gmail_users = []
        non_gmail_users = []
        
        for u in users:
            email_clean = (u.email or "").strip().lower()
            if email_clean.endswith("@gmail.com"):
                gmail_users.append(u)
            else:
                non_gmail_users.append(u)
                
        non_gmail_ids = [u.id for u in non_gmail_users]
        
        print(f"================================================================")
        print(f"MINDFUL METRICS - DATABASE CLEANUP AUDIT & DRY-RUN REPORT")
        print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
        print(f"Database: Supabase PostgreSQL (Remote)")
        print(f"================================================================")
        print(f"1. USER AUDIT:")
        print(f"   - Total Users in Database: {total_users}")
        print(f"   - Gmail Users to Retain (ends with '@gmail.com'): {len(gmail_users)}")
        print(f"   - Non-Gmail Users Proposed for Removal: {len(non_gmail_users)}")
        print()
        
        print(f"   Non-Gmail Users Detail:")
        for u in non_gmail_users:
            print(f"     * ID={u.id} | Name='{u.name}' | Email='{u.email}' | Role='{u.role}' | Dept='{u.department}'")
        print()
        
        # Check all related tables for records linked to non-gmail users
        related_counts = {}
        tables_to_check = [
            ("attendance", Attendance, Attendance.employee_id),
            ("leave_requests", LeaveRequest, LeaveRequest.employee_id),
            ("permission_requests", PermissionRequest, PermissionRequest.employee_id),
            ("tasks (employee_id)", Task, Task.employee_id),
            ("tasks (assigned_by_id)", Task, Task.assigned_by_id),
            ("surveys", Survey, Survey.employee_id),
            ("pulse_surveys", PulseSurvey, PulseSurvey.employee_id),
            ("communication", Communication, Communication.employee_id),
            ("predictions", Prediction, Prediction.employee_id),
            ("burnout_features", BurnoutFeatures, BurnoutFeatures.employee_id),
            ("notifications", Notification, Notification.employee_id),
            ("audit_logs", AuditLog, AuditLog.actor_id),
            ("interventions (employee_id)", Intervention, Intervention.employee_id),
            ("interventions (created_by_id)", Intervention, Intervention.created_by_id),
            ("attendance_corrections (employee_id)", AttendanceCorrection, AttendanceCorrection.employee_id),
            ("attendance_corrections (reviewed_by_id)", AttendanceCorrection, AttendanceCorrection.reviewed_by_id),
            ("departments (manager_id)", Department, Department.manager_id),
        ]
        
        print("2. ASSOCIATED RECORDS AUDIT:")
        for label, model, col in tables_to_check:
            total_tbl = db.query(model).count()
            linked_count = db.query(model).filter(col.in_(non_gmail_ids)).count() if non_gmail_ids else 0
            related_counts[label] = {
                "total": total_tbl,
                "linked_to_remove": linked_count,
                "retained": total_tbl - linked_count
            }
            print(f"   - {label:40s}: Total={total_tbl:4d} | Linked to Non-Gmail={linked_count:3d} | Retained={total_tbl - linked_count:4d}")
            
        print()
        print("3. SHARED / SYSTEM CONFIGURATION RECORDS (ALWAYS PRESERVED):")
        comp_settings = db.query(CompanySettings).count()
        holidays = db.query(Holiday).count()
        model_versions = db.query(ModelVersion).count()
        depts = db.query(Department).count()
        print(f"   - Company Settings: {comp_settings} (Preserved)")
        print(f"   - Configured Holidays: {holidays} (Preserved)")
        print(f"   - ML Model Versions: {model_versions} (Preserved)")
        print(f"   - Departments: {depts} (Preserved)")
        print()
        
        print("4. SUMMARY BY ROLE AMONG GMAIL USERS TO RETAIN:")
        role_counts = {}
        for u in gmail_users:
            r = (u.role or "unknown").lower()
            role_counts[r] = role_counts.get(r, 0) + 1
        for r, cnt in role_counts.items():
            print(f"   - {r.upper():10s}: {cnt}")
            
        print()
        print("5. EXPECTED FINAL STATE UPON APPROVED EXECUTION:")
        print(f"   - Retained Users: {len(gmail_users)} (All ending with @gmail.com)")
        print(f"   - Deleted Users: {len(non_gmail_users)}")
        print(f"================================================================")
        
    finally:
        db.close()

if __name__ == "__main__":
    run_dry_run()
