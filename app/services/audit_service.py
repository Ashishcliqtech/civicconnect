from ..extensions import db
from ..models import AuditLog


def log_action(actor, action, entity_type, entity_id=None, details=""):
    """Add an audit row to the current session (caller commits)."""
    db.session.add(AuditLog(actor_id=getattr(actor, "id", None), action=action,
                            entity_type=entity_type, entity_id=entity_id, details=details[:1000]))
