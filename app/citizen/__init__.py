from flask import Blueprint

bp = Blueprint("citizen", __name__)

from . import routes  # noqa: E402,F401
