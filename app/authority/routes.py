from flask import render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import current_user
from . import bp
from .forms import StatusForm, RejectForm, NoteForm, InfoRequestForm, ResolutionForm
from ..models import Complaint, Category
from ..services import complaint_service as cs, stats_service as stats
from ..services.complaint_service import ServiceError
from ..services.upload_service import save_image, UploadError
from ..utils.decorators import authority_required
from ..utils.helpers import get_or_404, user_can_access_complaint


def _dept_criteria():
    # Officers without a department see nothing (department_id == None never matches).
    return [Complaint.department_id == current_user.department_id] if current_user.department_id else [Complaint.id < 0]


def _complaint(cid):
    c = get_or_404(Complaint, cid)
    if not user_can_access_complaint(current_user, c):
        abort(403)
    return c


@bp.route("/dashboard")
@authority_required
def dashboard():
    crit = _dept_criteria()
    summary = stats.status_summary(crit)
    return render_template("authority/dashboard.html", summary=summary,
                           avg_days=stats.avg_resolution_days(crit), cat_chart=stats.by_category(crit),
                           trend=stats.monthly_trend(crit),
                           urgent=Complaint.query.filter(*crit, Complaint.status.in_(stats.PENDING))
                           .order_by(Complaint.created_at).limit(5).all())


@bp.route("/complaints")
@authority_required
def complaints():
    query = cs.filter_complaints(Complaint.query.filter(*_dept_criteria()), request.args)
    pagination = query.paginate(page=request.args.get("page", 1, type=int),
                                per_page=current_app.config["PER_PAGE"], error_out=False)
    categories = [c.name for c in Category.query.order_by(Category.name)]
    return render_template("authority/complaints.html", pagination=pagination, categories=categories)


@bp.route("/complaints/<int:cid>")
@authority_required
def complaint_detail(cid):
    c = _complaint(cid)
    status_form = StatusForm()
    status_form.status.choices = [(s, s) for s in cs.allowed_manual_targets(c, current_user)]
    return render_template("authority/complaint_detail.html", c=c, updates=c.updates, status_form=status_form,
                           reject_form=RejectForm(), note_form=NoteForm(), info_form=InfoRequestForm(),
                           resolution_form=ResolutionForm())


def _run(cid, action, success):
    """Run a service call, flash the outcome, and return to the detail page."""
    c = _complaint(cid)
    try:
        action(c)
        flash(success, "success")
    except ServiceError as e:
        flash(str(e), "error")
    return redirect(url_for("authority.complaint_detail", cid=cid))


@bp.route("/complaints/<int:cid>/accept", methods=["POST"])
@authority_required
def accept(cid):
    return _run(cid, lambda c: cs.accept(c, current_user), "Complaint accepted and moved to In Progress.")


@bp.route("/complaints/<int:cid>/reject", methods=["POST"])
@authority_required
def reject(cid):
    form = RejectForm()
    if not form.validate_on_submit():
        flash("A reason (5+ characters) is required to reject.", "error")
        return redirect(url_for("authority.complaint_detail", cid=cid))
    return _run(cid, lambda c: cs.reject(c, current_user, form.reason.data), "Complaint rejected.")


@bp.route("/complaints/<int:cid>/status", methods=["POST"])
@authority_required
def status(cid):
    c = _complaint(cid)
    form = StatusForm()
    form.status.choices = [(s, s) for s in cs.allowed_manual_targets(c, current_user)]
    if not form.validate_on_submit():
        flash("Choose a valid status.", "error")
        return redirect(url_for("authority.complaint_detail", cid=cid))
    return _run(cid, lambda c: cs.update_status(c, form.status.data, current_user, form.message.data), "Status updated.")


@bp.route("/complaints/<int:cid>/note", methods=["POST"])
@authority_required
def note(cid):
    form = NoteForm()
    if not form.validate_on_submit():
        flash("Note cannot be empty.", "error")
        return redirect(url_for("authority.complaint_detail", cid=cid))
    return _run(cid, lambda c: cs.add_note(c, current_user, form.message.data, "internal"), "Internal note saved.")


@bp.route("/complaints/<int:cid>/request-info", methods=["POST"])
@authority_required
def request_info(cid):
    form = InfoRequestForm()
    if not form.validate_on_submit():
        flash("Please describe what information you need.", "error")
        return redirect(url_for("authority.complaint_detail", cid=cid))
    return _run(cid, lambda c: cs.request_info(c, current_user, form.message.data), "Request sent to the citizen.")


@bp.route("/complaints/<int:cid>/resolve", methods=["POST"])
@authority_required
def resolve(cid):
    form = ResolutionForm()
    if not form.validate_on_submit():
        flash("Describe the action taken (10+ characters) and use an image file for proof.", "error")
        return redirect(url_for("authority.complaint_detail", cid=cid))
    try:
        filename = save_image(form.proof.data)
    except UploadError as e:
        flash(str(e), "error")
        return redirect(url_for("authority.complaint_detail", cid=cid))
    return _run(cid, lambda c: cs.submit_resolution(c, current_user, form.action_taken.data, filename),
                "Resolution submitted. An administrator will verify it.")
