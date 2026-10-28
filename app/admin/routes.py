import csv
import io
from flask import render_template, redirect, url_for, flash, request, abort, current_app, Response
from flask_login import current_user
from sqlalchemy import func
from . import bp
from .forms import UserForm, DepartmentForm, CategoryForm, AssignForm, ReopenForm
from ..extensions import db
from ..models import User, Department, Category, Complaint, AuditLog, Resolution, Feedback
from ..services import complaint_service as cs, stats_service as stats, audit_service
from ..services.complaint_service import ServiceError
from ..utils.decorators import admin_required
from ..utils.helpers import get_or_404


def _page():
    return request.args.get("page", 1, type=int)


@bp.route("/dashboard")
@admin_required
def dashboard():
    summary = stats.status_summary()
    recent = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()
    awaiting = Resolution.query.filter(Resolution.verified_at.is_(None)).count()
    return render_template("admin/dashboard.html", summary=summary, citizens=stats.platform_counts()["citizens"],
                           dept_chart=stats.by_department(), cat_chart=stats.by_category(),
                           trend=stats.monthly_trend(months=6), avg_days=stats.avg_resolution_days(),
                           recent=recent, awaiting=awaiting)


@bp.route("/complaints")
@admin_required
def complaints():
    query = cs.filter_complaints(Complaint.query, request.args)
    pagination = query.paginate(page=_page(), per_page=current_app.config["PER_PAGE"], error_out=False)
    return render_template("admin/complaints.html", pagination=pagination,
                           categories=[c.name for c in Category.query.order_by(Category.name)],
                           departments=Department.query.order_by(Department.name).all())


@bp.route("/complaints/<int:cid>")
@admin_required
def complaint_detail(cid):
    c = get_or_404(Complaint, cid)
    assign_form = AssignForm(department_id=c.department_id or 0, officer_id=c.assigned_officer_id or 0, priority=c.priority)
    return render_template("admin/complaint_detail.html", c=c, updates=c.updates, assign_form=assign_form,
                           reopen_form=ReopenForm())


@bp.route("/complaints/<int:cid>/assign", methods=["POST"])
@admin_required
def assign(cid):
    c = get_or_404(Complaint, cid)
    form = AssignForm()
    if form.validate_on_submit():
        try:
            cs.assign(c, current_user, form.department_id.data, form.officer_id.data or None, form.priority.data)
            flash("Complaint assigned.", "success")
        except ServiceError as e:
            flash(str(e), "error")
    else:
        flash("Invalid assignment.", "error")
    return redirect(url_for("admin.complaint_detail", cid=cid))


@bp.route("/complaints/<int:cid>/reopen", methods=["POST"])
@admin_required
def reopen(cid):
    c = get_or_404(Complaint, cid)
    form = ReopenForm()
    try:
        if not form.validate_on_submit():
            raise ServiceError("A reason is required.")
        cs.reopen(c, current_user, form.reason.data)
        flash("Complaint reopened.", "success")
    except ServiceError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.complaint_detail", cid=cid))


@bp.route("/resolutions/<int:rid>/verify", methods=["POST"])
@admin_required
def verify(rid):
    res = get_or_404(Resolution, rid)
    try:
        cs.verify_resolution(res, current_user)
        flash("Resolution verified.", "success")
    except ServiceError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.complaint_detail", cid=res.complaint_id))


# ---- Users -------------------------------------------------------------------
@bp.route("/users")
@admin_required
def users():
    query = User.query
    if request.args.get("role") in User.ROLES:
        query = query.filter_by(role=request.args["role"])
    if request.args.get("q"):
        like = f"%{request.args['q'].strip()}%"
        query = query.filter(User.full_name.ilike(like) | User.email.ilike(like))
    pagination = query.order_by(User.created_at.desc()).paginate(page=_page(), per_page=15, error_out=False)
    return render_template("admin/users.html", pagination=pagination)


@bp.route("/users/new", methods=["GET", "POST"])
@admin_required
def user_new():
    form = UserForm()
    if form.validate_on_submit():
        if not form.password.data:
            form.password.errors.append("Password is required for new users.")
        else:
            u = User(full_name=form.full_name.data.strip(), email=form.email.data.strip().lower(),
                     phone=form.phone.data or None, role=form.role.data, is_active=form.is_active.data,
                     department_id=form.department_id.data or None)
            u.set_password(form.password.data)
            db.session.add(u)
            db.session.flush()
            audit_service.log_action(current_user, "user_created", "user", u.id, f"{u.email} as {u.role}")
            db.session.commit()
            flash("User created.", "success")
            return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, user=None)


@bp.route("/users/<int:uid>/edit", methods=["GET", "POST"])
@admin_required
def user_edit(uid):
    u = get_or_404(User, uid)
    form = UserForm(obj=u, user=u)
    if form.validate_on_submit():
        if u.id == current_user.id and (form.role.data != "admin" or not form.is_active.data):
            flash("You cannot remove your own admin access or deactivate yourself.", "error")
        else:
            changes = []
            if u.role != form.role.data:
                changes.append(f"role {u.role}->{form.role.data}")
            if u.is_active != form.is_active.data:
                changes.append(f"active={form.is_active.data}")
            u.full_name, u.email = form.full_name.data.strip(), form.email.data.strip().lower()
            u.phone, u.role = form.phone.data or None, form.role.data
            u.is_active, u.department_id = form.is_active.data, form.department_id.data or None
            if form.password.data:
                u.set_password(form.password.data)
                changes.append("password reset")
            audit_service.log_action(current_user, "user_updated", "user", u.id, ", ".join(changes) or "profile edit")
            db.session.commit()
            flash("User updated.", "success")
            return redirect(url_for("admin.users"))
    form.department_id.data = form.department_id.data if request.method == "POST" else (u.department_id or 0)
    return render_template("admin/user_form.html", form=form, user=u)


# ---- Departments & categories ---------------------------------------------------
@bp.route("/departments", methods=["GET", "POST"])
@admin_required
def departments():
    form = DepartmentForm()
    if form.validate_on_submit():
        if Department.query.filter_by(name=form.name.data.strip()).first():
            flash("A department with that name already exists.", "error")
        else:
            d = Department(name=form.name.data.strip(), description=form.description.data,
                           contact_email=form.contact_email.data or None, is_active=form.is_active.data)
            db.session.add(d)
            db.session.flush()
            audit_service.log_action(current_user, "department_created", "department", d.id, d.name)
            db.session.commit()
            flash("Department created.", "success")
            return redirect(url_for("admin.departments"))
    return render_template("admin/departments.html", form=form, departments=Department.query.order_by(Department.name).all())


@bp.route("/departments/<int:did>/toggle", methods=["POST"])
@admin_required
def department_toggle(did):
    d = get_or_404(Department, did)
    d.is_active = not d.is_active  # departments are deactivated, never deleted (keeps history)
    audit_service.log_action(current_user, "department_toggled", "department", d.id, f"active={d.is_active}")
    db.session.commit()
    flash(f"{d.name} is now {'active' if d.is_active else 'inactive'}.", "success")
    return redirect(url_for("admin.departments"))


@bp.route("/categories", methods=["GET", "POST"])
@admin_required
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        cat = Category(name=form.name.data.strip(), icon=form.icon.data or "alert-circle")
        db.session.add(cat)
        db.session.flush()
        audit_service.log_action(current_user, "category_created", "category", cat.id, cat.name)
        db.session.commit()
        flash("Category added.", "success")
        return redirect(url_for("admin.categories"))
    return render_template("admin/categories.html", form=form, categories=Category.query.order_by(Category.name).all())


@bp.route("/categories/<int:cid>/toggle", methods=["POST"])
@admin_required
def category_toggle(cid):
    cat = get_or_404(Category, cid)
    cat.is_active = not cat.is_active
    audit_service.log_action(current_user, "category_toggled", "category", cat.id, f"active={cat.is_active}")
    db.session.commit()
    return redirect(url_for("admin.categories"))


# ---- Reports, audit ---------------------------------------------------------------
@bp.route("/reports")
@admin_required
def reports():
    ratings = db.session.query(func.avg(Feedback.rating)).scalar()
    return render_template("admin/reports.html", summary=stats.status_summary(), trend=stats.monthly_trend(months=12),
                           dept_chart=stats.by_department(), cat_chart=stats.by_category(),
                           perf=stats.resolution_by_department(), avg_days=stats.avg_resolution_days(),
                           avg_rating=round(ratings, 2) if ratings else None)


@bp.route("/reports/export.csv")
@admin_required
def export_csv():
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["reference", "title", "category", "status", "priority", "department", "created_at", "resolved_at"])
    for c in Complaint.query.order_by(Complaint.created_at.desc()).all():
        w.writerow([c.reference_number, c.title, c.category, c.status, c.priority,
                    c.department.name if c.department else "", c.created_at, c.resolved_at or ""])
    audit_service.log_action(current_user, "report_exported", "report", None, "complaints.csv")
    db.session.commit()
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=complaints.csv"})


@bp.route("/audit-log")
@admin_required
def audit_log():
    pagination = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(page=_page(), per_page=20, error_out=False)
    return render_template("admin/audit_log.html", pagination=pagination)
