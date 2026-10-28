"""Role-based access control. These run on the SERVER for every protected route."""
from functools import wraps
from flask import abort
from flask_login import current_user, login_required


def role_required(*roles):
    """Allow only logged-in users whose role is in `roles`; otherwise 403."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


citizen_required = role_required("citizen")
authority_required = role_required("authority")
admin_required = role_required("admin")
staff_required = role_required("authority", "admin")
