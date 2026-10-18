from sqlalchemy import text
from app.database import engine

def migrate_notifications():
    statements = [
        # Add new columns safely
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS notification_type VARCHAR(60) DEFAULT 'GENERAL';",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS entity_type VARCHAR(40) NULL;",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS entity_id VARCHAR(60) NULL;",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS is_read BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS read_at TIMESTAMP WITHOUT TIME ZONE NULL;",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP WITHOUT TIME ZONE NULL;",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS dedup_key VARCHAR(160) NULL;",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS group_key VARCHAR(100) NULL;",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'normal';",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS link_url VARCHAR(160) NULL;",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITHOUT TIME ZONE NULL;",

        # Backfill is_read from unread
        "UPDATE notifications SET is_read = TRUE WHERE unread = 0 AND (is_read IS NULL OR is_read = FALSE);",
        "UPDATE notifications SET is_read = FALSE WHERE (unread IS NULL OR unread > 0) AND is_read IS NULL;",
        "UPDATE notifications SET is_archived = FALSE WHERE is_archived IS NULL;",
        "UPDATE notifications SET priority = 'normal' WHERE priority IS NULL;",
        "UPDATE notifications SET notification_type = 'GENERAL' WHERE notification_type IS NULL;",

        # Performance indexes
        "CREATE INDEX IF NOT EXISTS idx_notifications_recipient_active ON notifications (employee_id, is_archived, created_at DESC);",
        "CREATE INDEX IF NOT EXISTS idx_notifications_recipient_unread ON notifications (employee_id, is_read, is_archived);",
        "CREATE INDEX IF NOT EXISTS idx_notifications_dedup_key ON notifications (dedup_key);",
        "CREATE INDEX IF NOT EXISTS idx_notifications_group_key ON notifications (group_key);"
    ]

    print("Connecting to database and running notification migrations...")
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
            print(f"Executed: {stmt.split()[0]} {stmt.split()[1]} {stmt.split()[2] if len(stmt.split()) > 2 else ''}")

    print("Notification migration completed successfully!")

if __name__ == "__main__":
    migrate_notifications()
