from flask import Blueprint

bp = Blueprint("authority", __name__)

from . import routes  # noqa: E402,F401
