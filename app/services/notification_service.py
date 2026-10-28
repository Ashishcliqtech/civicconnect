from ..extensions import db
from ..models import Notification, User


def notify(user_id, title, message, complaint_id=None):
    """Create an in-app notification (caller commits). Email is optional/not required."""
    if user_id:
        db.session.add(Notification(user_id=user_id, complaint_id=complaint_id,
                                    title=title, message=message))


def notify_department(department_id, title, message, complaint_id=None):
    if not department_id:
        return
    officers = User.query.filter_by(department_id=department_id, role=User.ROLE_AUTHORITY,
                                    is_active=True).all()
    for officer in officers:
        notify(officer.id, title, message, complaint_id)


def unread_count(user):
    return Notification.query.filter_by(user_id=user.id, is_read=False).count()
