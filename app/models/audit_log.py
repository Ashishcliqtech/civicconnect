from .user import utcnow
from ..extensions import db


class AuditLog(db.Model):
    """Append-only record of important actions. actor_id has no cascade so logs survive."""
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(60), nullable=False, index=True)
    entity_type = db.Column(db.String(40), nullable=False)
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    actor = db.relationship("User")
