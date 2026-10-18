from __future__ import annotations
import os
import sys
from pathlib import Path

# Add backend root to sys.path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base, engine as target_engine
from app.models import (
    CompanySettings, Department, User, Attendance, LeaveRequest,
    PermissionRequest, SurveyQuestion, Survey, PulseSurvey, Task,
    Communication, Prediction, BurnoutFeatures, Notification,
    AuditLog, ModelVersion, Intervention
)

SQLITE_PATH = ROOT / "mindful_metrics_backup.db"
if not SQLITE_PATH.exists():
    SQLITE_PATH = ROOT / "mindful_metrics.db"

sqlite_engine = create_engine(f"sqlite:///{SQLITE_PATH}", connect_args={"check_same_thread": False})
SqliteSession = sessionmaker(bind=sqlite_engine)
TargetSession = sessionmaker(bind=target_engine)

TABLE_ORDER = [
    CompanySettings,
    Department,
    User,
    Attendance,
    LeaveRequest,
    PermissionRequest,
    SurveyQuestion,
    Survey,
    PulseSurvey,
    Task,
    Communication,
    Prediction,
    BurnoutFeatures,
    Notification,
    AuditLog,
    ModelVersion,
    Intervention,
]

def migrate():
    print("[1/4] Creating all schema tables in target PostgreSQL database...")
    Base.metadata.create_all(bind=target_engine)
    print("      -> Tables verified.")

    print(f"[2/4] Reading data from SQLite ({SQLITE_PATH.name})...")
    s_db = SqliteSession()
    t_db = TargetSession()

    try:
        total_migrated = 0
        user_mgr_map = {}

        for model in TABLE_ORDER:
            records = s_db.query(model).all()
            if not records:
                continue

            count = 0
            for r in records:
                existing = t_db.query(model).filter(model.id == r.id).first()
                if not existing:
                    data = {c.name: getattr(r, c.name) for c in model.__table__.columns}
                    # For User, defer manager_id to avoid self-referencing foreign key violation before manager is inserted
                    if model == User and data.get("manager_id"):
                        user_mgr_map[r.id] = data["manager_id"]
                        data["manager_id"] = None

                    new_obj = model(**data)
                    t_db.add(new_obj)
                    count += 1

            t_db.commit()
            print(f"      -> {model.__tablename__}: {count} rows migrated.")
            total_migrated += count

        # Restore User manager_id references
        if user_mgr_map:
            print("[3/4] Linking user hierarchy (manager_id relations)...")
            for uid, mgr_id in user_mgr_map.items():
                u = t_db.query(User).filter(User.id == uid).first()
                if u:
                    u.manager_id = mgr_id
            t_db.commit()
            print(f"      -> {len(user_mgr_map)} manager relationships linked.")
        else:
            print("[3/4] User hierarchy check complete.")

        # Sync PostgreSQL primary key sequences so auto-increment continues seamlessly
        print("[4/4] Synchronizing PostgreSQL ID sequences...")
        with target_engine.connect() as conn:
            for model in TABLE_ORDER:
                tbl = model.__tablename__
                try:
                    conn.execute(text(f"""
                        SELECT setval(
                            pg_get_serial_sequence('{tbl}', 'id'),
                            COALESCE((SELECT MAX(id) FROM {tbl}), 1)
                        );
                    """))
                    conn.commit()
                except Exception:
                    pass
        print("      -> Sequences synchronized.")

        print(f"\n[SUCCESS] Migration Complete! Total {total_migrated} rows successfully transferred to Supabase PostgreSQL.")
    except Exception as e:
        t_db.rollback()
        print(f"\n[ERROR] Migration failed: {e}")
    finally:
        s_db.close()
        t_db.close()

if __name__ == "__main__":
    migrate()
