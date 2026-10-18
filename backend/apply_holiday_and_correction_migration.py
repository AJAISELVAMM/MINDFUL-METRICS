"""
Migration script: Pre-seed all 24 supplied 2026 Tamil Nadu Government Public Holidays
and create attendance_corrections table in Supabase PostgreSQL.

Executes safely and idempotently.
"""
from __future__ import annotations
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal, Base
from app.models import Holiday, AttendanceCorrection
from app.services.holiday_service import seed_2026_holidays, SUPPLIED_2026_HOLIDAYS, SOURCE_NAME, SOURCE_REF


def run_migration():
    print("[MIGRATION] Starting database migration for Holidays and Attendance Corrections...")
    
    # 1. Create tables if they do not exist
    print("[MIGRATION] Ensuring tables 'holidays' and 'attendance_corrections' exist in PostgreSQL...")
    Base.metadata.create_all(bind=engine, tables=[Holiday.__table__, AttendanceCorrection.__table__])
    print("[MIGRATION] Tables verified/created successfully.")

    # 2. Run Idempotent Seed
    db = SessionLocal()
    try:
        print("[MIGRATION] Seeding 24 supplied 2026 Tamil Nadu Government Public Holidays...")
        res = seed_2026_holidays(db)
        print(f"[MIGRATION] Result: inserted={res['inserted']}, already_existing={res['already_existing']}, total_2026={res['total_2026_holidays']}")
        
        # 3. Verify Idempotency (re-run immediately)
        print("[MIGRATION] Testing seed idempotency...")
        res_rerun = seed_2026_holidays(db)
        assert res_rerun["inserted"] == 0, "Idempotency failed: second run inserted new records!"
        assert res_rerun["total_2026_holidays"] == 24, f"Expected 24 holidays, found {res_rerun['total_2026_holidays']}"
        print("[MIGRATION] Idempotency test passed (0 new rows on re-run).")

        # 4. Detailed query verification
        holidays_in_db = db.query(Holiday).filter(Holiday.calendar_year == 2026).order_by(Holiday.holiday_date.asc()).all()
        print(f"[MIGRATION] Verified {len(holidays_in_db)} holiday records in database:")
        for idx, h in enumerate(holidays_in_db, 1):
            print(f"  {idx:2d}. {h.holiday_date} | {h.holiday_name:<65} | Type: {h.holiday_type:<14} | Applicability: {h.applicability}")

        # Check Bank Holiday applicability
        from datetime import date
        bank_h = db.query(Holiday).filter(Holiday.holiday_date == date(2026, 4, 1)).first()
        assert bank_h is not None, "Bank holiday record missing!"
        assert bank_h.applicability == "bank_only", f"Bank holiday applicability incorrect: {bank_h.applicability}"
        print("[MIGRATION] Bank holiday applicability verified: 'bank_only' on 2026-04-01.")

        print("[MIGRATION] SUCCESS! All 24 supplied 2026 Tamil Nadu Government public holidays verified.")
        return True
    finally:
        db.close()


if __name__ == "__main__":
    success = run_migration()
    if not success:
        sys.exit(1)
