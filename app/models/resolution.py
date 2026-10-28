from .user import utcnow
from ..extensions import db


class Resolution(db.Model):
    __tablename__ = "resolutions"
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaints.id"), nullable=False, index=True)
    officer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action_taken = db.Column(db.Text, nullable=False)
    proof_photo_filename = db.Column(db.String(100))
    submitted_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    verified_by_admin_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    verified_at = db.Column(db.DateTime)

    complaint = db.relationship("Complaint", back_populates="resolutions")
    officer = db.relationship("User", foreign_keys=[officer_id])
    verified_by = db.relationship("User", foreign_keys=[verified_by_admin_id])
