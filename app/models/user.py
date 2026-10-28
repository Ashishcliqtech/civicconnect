from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db, login_manager


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    ROLE_CITIZEN, ROLE_AUTHORITY, ROLE_ADMIN = "citizen", "authority", "admin"
    ROLES = (ROLE_CITIZEN, ROLE_AUTHORITY, ROLE_ADMIN)

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_CITIZEN, index=True)
    phone = db.Column(db.String(20))
    # Officers belong to one department (needed to scope what they can see).
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (db.CheckConstraint("role IN ('citizen','authority','admin')", name="ck_user_role"),)

    department = db.relationship("Department", back_populates="officers", foreign_keys=[department_id])
    complaints = db.relationship("Complaint", back_populates="author", foreign_keys="Complaint.user_id")
    notifications = db.relationship("Notification", back_populates="user")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_authority(self):
        return self.role == self.ROLE_AUTHORITY

    @property
    def is_citizen(self):
        return self.role == self.ROLE_CITIZEN

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(User, int(user_id))
    # Deactivated users are logged out on their next request.
    return user if user and user.is_active else None
