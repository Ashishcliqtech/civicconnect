"""CivicConnect application factory."""
import os
from flask import Flask, render_template, flash, redirect, request, url_for
from flask_login import current_user
from config import config_by_name
from .extensions import db, migrate, login_manager, csrf


def create_app(config_name=None):
    app = Flask(__name__, instance_relative_config=True)
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    # config_name may be "development"/"production"/"testing" or a config class (used by tests)
    cfg = config_name if isinstance(config_name, type) else config_by_name.get(config_name, config_by_name["development"])
    app.config.from_object(cfg)

    if config_name == "production" and app.config["SECRET_KEY"] == "dev-only-insecure-key":
        raise RuntimeError("SECRET_KEY must be set in production.")

    os.makedirs(app.config["DATA_DIR"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import models  # noqa: F401  (registers models for migrations)
    from .auth import bp as auth_bp
    from .citizen import bp as citizen_bp
    from .authority import bp as authority_bp
    from .admin import bp as admin_bp
    from .public import bp as public_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(citizen_bp, url_prefix="/citizen")
    app.register_blueprint(authority_bp, url_prefix="/authority")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    register_template_helpers(app)
    register_error_handlers(app)
    from .cli import register_cli
    register_cli(app)

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return resp

    return app


def register_template_helpers(app):
    from .models import Complaint
    from .services.notification_service import unread_count

    @app.context_processor
    def inject_globals():
        unread = unread_count(current_user) if current_user.is_authenticated else 0
        return {"unread_notifications": unread, "STATUSES": Complaint.STATUSES,
                "PRIORITIES": Complaint.PRIORITIES}

    @app.template_filter("dt")
    def format_dt(value, fmt="%d %b %Y, %H:%M"):
        return value.strftime(fmt) if value else "—"

    @app.template_filter("slug")
    def slug(value):
        return (value or "").lower().replace(" ", "-")


def register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(429)
    def too_many(e):
        return render_template("errors/429.html"), 429

    @app.errorhandler(413)
    def too_large(e):
        flash("The uploaded file is too large.", "error")
        return redirect(request.referrer or url_for("public.index"))

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()  # never leave a broken transaction open
        return render_template("errors/500.html"), 500
