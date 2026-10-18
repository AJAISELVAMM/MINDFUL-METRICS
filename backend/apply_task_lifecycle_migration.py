"""
Database migration script:
1. Add task lifecycle and verification columns to 'tasks' table in PostgreSQL.
2. Create 'task_unblock_requests' table.
Executes safely and idempotently.
"""
from __future__ import annotations
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal, Base
from app.models import Task, TaskUnblockRequest
from sqlalchemy import text


def run_migration():
    print("[MIGRATION] Starting Task Lifecycle & Verification Migration...")

    with engine.begin() as conn:
        # 1. Add columns to tasks table if not existing
        alter_statements = [
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completed_by_id INTEGER REFERENCES users(id)",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS verification_status VARCHAR(40) DEFAULT 'None'",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS verified_by_id INTEGER REFERENCES users(id)",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS verification_notes TEXT",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS missed_deadline_at TIMESTAMP",
        ]
        for stmt in alter_statements:
            print(f"[MIGRATION] Executing: {stmt}")
            conn.execute(text(stmt))

        # 2. Update existing completed tasks to have verification_status if None
        conn.execute(text("UPDATE tasks SET verification_status = 'Awaiting Verification' WHERE status = 'Completed' AND (verification_status IS NULL OR verification_status = 'None')"))

    # 3. Create task_unblock_requests table
    print("[MIGRATION] Creating table 'task_unblock_requests' if not exists...")
    Base.metadata.create_all(bind=engine, tables=[TaskUnblockRequest.__table__])

    # 4. Verify columns
    from sqlalchemy import inspect
    insp = inspect(engine)
    tasks_cols = [c["name"] for c in insp.get_columns("tasks")]
    unblock_cols = [c["name"] for c in insp.get_columns("task_unblock_requests")]
    print(f"[MIGRATION] Verified 'tasks' columns: {tasks_cols}")
    print(f"[MIGRATION] Verified 'task_unblock_requests' columns: {unblock_cols}")
    print("[MIGRATION] SUCCESS! Task lifecycle migration applied successfully.")
    return True


if __name__ == "__main__":
    run_migration()
