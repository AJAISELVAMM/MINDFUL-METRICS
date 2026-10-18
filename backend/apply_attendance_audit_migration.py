from app.database import engine
from sqlalchemy import text

print("Applying attendance schema migration with direct SQL...")

with engine.begin() as conn:
    if not str(engine.url).startswith("sqlite"):
        conn.execute(text("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS arrival_status VARCHAR(20) DEFAULT 'ON_TIME';"))
        conn.execute(text("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS attendance_day_value FLOAT DEFAULT 1.0;"))
        conn.execute(text("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS finalized_at TIMESTAMP NULL;"))
        print("Columns verified.")

        # Fast set arrival_status
        conn.execute(text("""
            UPDATE attendance 
            SET arrival_status = 'LATE'
            WHERE (late_minutes IS NOT NULL AND late_minutes > 0)
               OR (check_in_at IS NOT NULL AND check_in_at::time > '09:30:00'::time);
        """))
        conn.execute(text("""
            UPDATE attendance 
            SET arrival_status = 'ON_TIME'
            WHERE (check_in IS NOT NULL OR check_in_at IS NOT NULL)
              AND (arrival_status IS NULL OR arrival_status != 'LATE');
        """))

        # Fast set attendance_day_value
        conn.execute(text("""
            UPDATE attendance 
            SET attendance_day_value = 1.0
            WHERE final_status IN ('FULL_DAY_PRESENT', 'PRESENT_WITH_APPROVED_PERMISSION', 'LATE_PRESENT', 'WORKING')
               OR status IN ('Completed', 'Present');
        """))
        conn.execute(text("""
            UPDATE attendance 
            SET attendance_day_value = 0.5
            WHERE final_status IN ('MORNING_HALF_DAY_ABSENT', 'HALF_DAY_LEAVE', 'HALF_DAY');
        """))
        conn.execute(text("""
            UPDATE attendance 
            SET attendance_day_value = 0.0
            WHERE final_status IN ('ABSENT', 'WEEKLY_OFF', 'HOLIDAY', 'FULL_DAY_LEAVE');
        """))
        print("PostgreSQL fast migration complete!")
    else:
        # SQLite
        res = conn.exec_driver_sql("PRAGMA table_info(attendance)").fetchall()
        cols = [r[1] for r in res]
        if "arrival_status" not in cols:
            conn.exec_driver_sql("ALTER TABLE attendance ADD COLUMN arrival_status VARCHAR(20) DEFAULT 'ON_TIME'")
        if "attendance_day_value" not in cols:
            conn.exec_driver_sql("ALTER TABLE attendance ADD COLUMN attendance_day_value FLOAT DEFAULT 1.0")
        if "finalized_at" not in cols:
            conn.exec_driver_sql("ALTER TABLE attendance ADD COLUMN finalized_at TIMESTAMP NULL")
        print("SQLite columns added.")

print("Migration finished successfully.")
