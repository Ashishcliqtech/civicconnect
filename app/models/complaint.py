from .user import utcnow
from ..extensions import db


class Complaint(db.Model):
    __tablename__ = "complaints"

    STATUS_SUBMITTED, STATUS_REVIEW, STATUS_ASSIGNED = "Submitted", "Under Review", "Assigned"
    STATUS_PROGRESS, STATUS_RESOLVED, STATUS_REJECTED = "In Progress", "Resolved", "Rejected"
    STATUS_WITHDRAWN = "Withdrawn"
    STATUSES = (STATUS_SUBMITTED, STATUS_REVIEW, STATUS_ASSIGNED, STATUS_PROGRESS,
                STATUS_RESOLVED, STATUS_REJECTED, STATUS_WITHDRAWN)
    PRIORITIES = ("Low", "Medium", "High", "Critical")

    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), nullable=False, index=True)
    address = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    photo_filename = db.Column(db.String(100))
    priority = db.Column(db.String(10), nullable=False, default="Medium")
    status = db.Column(db.String(20), nullable=False, default=STATUS_SUBMITTED, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), index=True)
    assigned_officer_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime)

    __table_args__ = (
        db.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_complaint_lat"),
        db.CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_complaint_lng"),
        db.CheckConstraint("priority IN ('Low','Medium','High','Critical')", name="ck_complaint_priority"),
    )

    author = db.relationship("User", back_populates="complaints", foreign_keys=[user_id])
    officer = db.relationship("User", foreign_keys=[assigned_officer_id])
    department = db.relationship("Department", back_populates="complaints")
    # No delete cascades: complaints are never hard-deleted so audit history survives.
    updates = db.relationship("ComplaintUpdate", back_populates="complaint",
                              order_by="ComplaintUpdate.created_at, ComplaintUpdate.id")
    resolutions = db.relationship("Resolution", back_populates="complaint",
                                  order_by="Resolution.submitted_at")
    feedback = db.relationship("Feedback", back_populates="complaint", uselist=False)

    @property
    def latest_resolution(self):
        return self.resolutions[-1] if self.resolutions else None

    @property
    def public_updates(self):
        return [u for u in self.updates if u.visibility == "public"]

    @property
    def is_open(self):
        return self.status not in (self.STATUS_RESOLVED, self.STATUS_REJECTED, self.STATUS_WITHDRAWN)
