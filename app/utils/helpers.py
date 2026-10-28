from urllib.parse import urlparse, urljoin
from flask import request, abort
from ..extensions import db


def is_safe_redirect(target):
    """Prevent open-redirect attacks via ?next=."""
    if not target:
        return False
    host = urlparse(request.host_url)
    test = urlparse(urljoin(request.host_url, target))
    return test.scheme in ("http", "https") and host.netloc == test.netloc


def get_or_404(model, ident):
    obj = db.session.get(model, ident)
    if obj is None:
        abort(404)
    return obj


def user_can_access_complaint(user, complaint):
    """Single source of truth for who may open a complaint's private details."""
    if user.is_admin:
        return True
    if user.is_citizen:
        return complaint.user_id == user.id
    if user.is_authority:
        return complaint.department_id is not None and complaint.department_id == user.department_id
    return False


def short_text(text, length=120):
    text = text or ""
    return text if len(text) <= length else text[: length - 1] + "…"
