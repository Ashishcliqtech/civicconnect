from flask import render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import current_user
from . import bp
from .forms import ComplaintForm, FeedbackForm, CommentForm
from ..models import Complaint, Category
from ..services import complaint_service as cs, stats_service as stats
from ..services.complaint_service import ServiceError
from ..services.upload_service import save_image, delete_image, UploadError
from ..utils.decorators import citizen_required
from ..utils.helpers import get_or_404
from ..utils.ratelimit import rate_limit


def _own_complaint(cid):
    c = get_or_404(Complaint, cid)
    if c.user_id != current_user.id:
        abort(403)  # privacy: citizens never see each other's private details
    return c


@bp.route("/dashboard")
@citizen_required
def dashboard():
    crit = [Complaint.user_id == current_user.id]
    summary = stats.status_summary(crit)
    recent = Complaint.query.filter(*crit).order_by(Complaint.updated_at.desc()).limit(5).all()
    status_chart = {"labels": ["Pending", "In progress", "Resolved", "Rejected"],
                    "values": [summary["pending"], summary["in_progress"], summary["resolved"], summary["rejected"]]}
    return render_template("citizen/dashboard.html", summary=summary, recent=recent, status_chart=status_chart)


@bp.route("/submit", methods=["GET", "POST"])
@citizen_required
@rate_limit(10, 3600)
def submit():
    form = ComplaintForm()
    if request.method == "GET" and request.args.get("category") in [c for c, _ in form.category.choices]:
        form.category.data = request.args["category"]  # pre-select from landing page cards
    if form.validate_on_submit():
        try:
            filename = save_image(form.photo.data)
        except UploadError as e:
            form.photo.errors.append(str(e))
            return render_template("citizen/submit.html", form=form, editing=False)
        c = cs.create_complaint(current_user, {k: getattr(form, k).data for k in
                                ("title", "category", "description", "address", "latitude", "longitude")}, filename)
        flash(f"Complaint submitted! Your reference number is {c.reference_number}.", "success")
        return redirect(url_for("citizen.complaint_detail", cid=c.id))
    return render_template("citizen/submit.html", form=form, editing=False)


@bp.route("/complaints")
@citizen_required
def my_complaints():
    query = cs.filter_complaints(Complaint.query.filter_by(user_id=current_user.id), request.args)
    page = request.args.get("page", 1, type=int)
    pagination = query.paginate(page=page, per_page=current_app.config["PER_PAGE"], error_out=False)
    categories = [c.name for c in Category.query.order_by(Category.name)]
    return render_template("citizen/my_complaints.html", pagination=pagination, categories=categories)


@bp.route("/complaints/<int:cid>")
@citizen_required
def complaint_detail(cid):
    c = _own_complaint(cid)
    return render_template("citizen/complaint_detail.html", c=c, feedback_form=FeedbackForm(),
                           comment_form=CommentForm(), updates=c.public_updates)


@bp.route("/complaints/<int:cid>/edit", methods=["GET", "POST"])
@citizen_required
def edit(cid):
    c = _own_complaint(cid)
    if c.status != Complaint.STATUS_SUBMITTED:
        flash("Only complaints that are still 'Submitted' can be edited.", "error")
        return redirect(url_for("citizen.complaint_detail", cid=cid))
    form = ComplaintForm(obj=c)
    if form.validate_on_submit():
        try:
            filename = save_image(form.photo.data)
            old = c.photo_filename
            cs.update_complaint(c, current_user, {k: getattr(form, k).data for k in
                                ("title", "category", "description", "address", "latitude", "longitude")}, filename)
            if filename:
                delete_image(old)
        except (UploadError, ServiceError) as e:
            flash(str(e), "error")
            return render_template("citizen/submit.html", form=form, editing=True, c=c)
        flash("Complaint updated.", "success")
        return redirect(url_for("citizen.complaint_detail", cid=cid))
    return render_template("citizen/submit.html", form=form, editing=True, c=c)


@bp.route("/complaints/<int:cid>/withdraw", methods=["POST"])
@citizen_required
def withdraw(cid):
    c = _own_complaint(cid)
    try:
        cs.withdraw(c, current_user)
        flash("Complaint withdrawn.", "success")
    except ServiceError as e:
        flash(str(e), "error")
    return redirect(url_for("citizen.complaint_detail", cid=cid))


@bp.route("/complaints/<int:cid>/comment", methods=["POST"])
@citizen_required
def comment(cid):
    c = _own_complaint(cid)
    form = CommentForm()
    if form.validate_on_submit():
        try:
            cs.add_citizen_comment(c, current_user, form.message.data)
            flash("Message sent.", "success")
        except ServiceError as e:
            flash(str(e), "error")
    else:
        flash("Message cannot be empty.", "error")
    return redirect(url_for("citizen.complaint_detail", cid=cid))


@bp.route("/complaints/<int:cid>/feedback", methods=["POST"])
@citizen_required
def feedback(cid):
    c = _own_complaint(cid)
    form = FeedbackForm()
    if form.validate_on_submit():
        try:
            cs.add_feedback(c, current_user, form.rating.data, form.comments.data)
            flash("Thank you for your feedback!", "success")
        except ServiceError as e:
            flash(str(e), "error")
    else:
        flash("Please give a rating between 1 and 5.", "error")
    return redirect(url_for("citizen.complaint_detail", cid=cid))
