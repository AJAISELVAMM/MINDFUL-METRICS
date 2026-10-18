from __future__ import annotations
import json
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import AuditLog, User


def log_audit(
    db: Session,
    actor: User | None,
    action: str,
    target_type: str,
    target_id: str | int,
    old_value: dict | str | None = None,
    new_value: dict | str | None = None,
):
    try:
        old_str = json.dumps(old_value) if isinstance(old_value, dict) else (str(old_value) if old_value else None)
        new_str = json.dumps(new_value) if isinstance(new_value, dict) else (str(new_value) if new_value else None)
        entry = AuditLog(
            actor_id=actor.id if actor else None,
            actor_name=actor.name if actor else "System",
            actor_role=actor.role if actor else "system",
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            old_value=old_str,
            new_value=new_str,
            timestamp=datetime.utcnow(),
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()
