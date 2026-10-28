from .user import utcnow
from ..extensions import db


class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, default="")
    contact_email = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    officers = db.relationship("User", back_populates="department", foreign_keys="User.department_id")
    complaints = db.relationship("Complaint", back_populates="department")

    def __repr__(self):
        return f"<Department {self.name}>"


class Category(db.Model):
    """Complaint categories are managed by admins (supporting model)."""
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    icon = db.Column(db.String(40), default="alert-circle")  # Lucide icon name
    is_active = db.Column(db.Boolean, nullable=False, default=True)
