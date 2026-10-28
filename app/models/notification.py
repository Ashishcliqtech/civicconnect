from .user import utcnow
from ..extensions import db


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaints.id"))
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="notifications")
    complaint = db.relationship("Complaint")
