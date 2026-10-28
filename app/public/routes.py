import os
from flask import render_template, abort, send_from_directory, current_app, request, jsonify
from flask_login import login_required, current_user
from . import bp
from ..models import Complaint, Category, Resolution
from ..services import stats_service as stats, complaint_service as cs
from ..utils.helpers import user_can_access_complaint, short_text

# Only these statuses are shown publicly; withdrawn/rejected complaints stay private.
PUBLIC_STATUSES = (Complaint.STATUS_SUBMITTED, Complaint.STATUS_REVIEW, Complaint.STATUS_ASSIGNED,
                   Complaint.STATUS_PROGRESS, Complaint.STATUS_RESOLVED)


def _public_query():
    return Complaint.query.filter(Complaint.status.in_(PUBLIC_STATUSES))


@bp.route("/")
def index():
    return render_template("public/index.html", counts=stats.platform_counts(),
                           categories=Category.query.filter_by(is_active=True).order_by(Category.name).all())


@bp.route("/about")
def about():
    return render_template("public/about.html")


@bp.route("/public-complaints")
def public_complaints():
    query = cs.filter_complaints(_public_query(), request.args)
    pagination = query.paginate(page=request.args.get("page", 1, type=int), per_page=10, error_out=False)
    return render_template("public/map.html", pagination=pagination,
                           categories=[c.name for c in Category.query.order_by(Category.name)])


@bp.route("/api/public/complaints")
def public_api():
    """Privacy-safe JSON for the map: no user data, no photos, coordinates rounded (~100 m)."""
    rows = cs.filter_complaints(_public_query(), request.args).limit(300).all()
    return jsonify([{"ref": c.reference_number, "title": short_text(c.title, 80), "category": c.category,
                     "status": c.status, "lat": round(c.latitude, 3), "lng": round(c.longitude, 3),
                     "date": c.created_at.strftime("%d %b %Y")} for c in rows])


@bp.route("/media/<path:filename>")
@login_required
def media(filename):
    """Private uploads are served only to people allowed to see the related complaint."""
    filename = os.path.basename(filename)
    complaint = Complaint.query.filter_by(photo_filename=filename).first()
    if complaint is None:
        res = Resolution.query.filter_by(proof_photo_filename=filename).first()
        complaint = res.complaint if res else None
    if complaint is None or not user_can_access_complaint(current_user, complaint):
        abort(404 if complaint is None else 403)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
