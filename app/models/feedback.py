from .user import utcnow
from ..extensions import db


class Feedback(db.Model):
    __tablename__ = "feedback"
    id = db.Column(db.Integer, primary_key=True)
    # unique=True enforces ONE feedback per complaint at the database level.
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaints.id"), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comments = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    __table_args__ = (db.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_feedback_rating"),)

    complaint = db.relationship("Complaint", back_populates="feedback")
    user = db.relationship("User")
