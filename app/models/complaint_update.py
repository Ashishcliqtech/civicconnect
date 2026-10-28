from .user import utcnow
from ..extensions import db


class ComplaintUpdate(db.Model):
    __tablename__ = "complaint_updates"
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaints.id"), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    old_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20))
    message = db.Column(db.Text, nullable=False, default="")
    visibility = db.Column(db.String(10), nullable=False, default="public")  # public | internal
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    __table_args__ = (db.CheckConstraint("visibility IN ('public','internal')", name="ck_update_visibility"),)

    complaint = db.relationship("Complaint", back_populates="updates")
    actor = db.relationship("User")
