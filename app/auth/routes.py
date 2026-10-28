from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from . import bp
from .forms import RegisterForm, LoginForm, ProfileForm
from ..extensions import db
from ..models import User, Notification
from ..services import audit_service
from ..utils.helpers import is_safe_redirect, get_or_404
from ..utils.ratelimit import rate_limit


def home_for(user):
    return url_for({"admin": "admin.dashboard", "authority": "authority.dashboard"}.get(user.role, "citizen.dashboard"))


@bp.route("/register", methods=["GET", "POST"])
@rate_limit(10, 600)
def register():
    if current_user.is_authenticated:
        return redirect(home_for(current_user))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(full_name=form.full_name.data.strip(), email=form.email.data.strip().lower(),
                    phone=(form.phone.data or "").strip() or None, role=User.ROLE_CITIZEN)  # public sign-up = citizen only
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Account created. Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
@rate_limit(10, 300)
def login():
    if current_user.is_authenticated:
        return redirect(home_for(current_user))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        # Same message for unknown email / wrong password / disabled account (no user enumeration).
        if user and user.is_active and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            nxt = request.args.get("next")
            return redirect(nxt if is_safe_redirect(nxt) else home_for(user))
        flash("Invalid email or password.", "error")
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("public.index"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data.strip()
        current_user.phone = (form.phone.data or "").strip() or None
        if form.new_password.data:
            if not form.current_password.data or not current_user.check_password(form.current_password.data):
                flash("Current password is incorrect.", "error")
                return render_template("auth/profile.html", form=form)
            current_user.set_password(form.new_password.data)
            audit_service.log_action(current_user, "password_changed", "user", current_user.id)
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("auth.profile"))
    return render_template("auth/profile.html", form=form)


@bp.route("/notifications")
@login_required
def notifications():
    page = request.args.get("page", 1, type=int)
    pagination = (Notification.query.filter_by(user_id=current_user.id)
                  .order_by(Notification.created_at.desc()).paginate(page=page, per_page=15, error_out=False))
    return render_template("auth/notifications.html", pagination=pagination)


@bp.route("/notifications/<int:nid>/read", methods=["POST"])
@login_required
def mark_read(nid):
    n = get_or_404(Notification, nid)
    if n.user_id != current_user.id:
        from flask import abort
        abort(403)
    n.is_read = True
    db.session.commit()
    if n.complaint_id:
        return redirect(url_for("auth.open_complaint", cid=n.complaint_id))
    return redirect(url_for("auth.notifications"))


@bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return redirect(url_for("auth.notifications"))


@bp.route("/notifications/count")
@login_required
def notification_count():
    from ..services.notification_service import unread_count
    return {"unread": unread_count(current_user)}


@bp.route("/complaint/<int:cid>")
@login_required
def open_complaint(cid):
    """Role-aware redirect so notifications link to the right detail page."""
    endpoint = {"admin": "admin.complaint_detail", "authority": "authority.complaint_detail"}.get(
        current_user.role, "citizen.complaint_detail")
    return redirect(url_for(endpoint, cid=cid))
