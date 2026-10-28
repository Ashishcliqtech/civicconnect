"""Dashboard metrics computed from real database rows. Every function takes `criteria`
(a list of SQLAlchemy filters) so each role only ever sees data it is allowed to see."""
from collections import OrderedDict
from datetime import datetime, timedelta
from sqlalchemy import func
from ..extensions import db
from ..models import Complaint, Department, User
from ..models.user import utcnow

PENDING = (Complaint.STATUS_SUBMITTED, Complaint.STATUS_REVIEW, Complaint.STATUS_ASSIGNED)


def status_summary(criteria=()):
    rows = (db.session.query(Complaint.status, func.count(Complaint.id))
            .filter(*criteria).group_by(Complaint.status).all())
    counts = dict(rows)
    return {
        "total": sum(counts.values()),
        "pending": sum(counts.get(s, 0) for s in PENDING),
        "in_progress": counts.get(Complaint.STATUS_PROGRESS, 0),
        "resolved": counts.get(Complaint.STATUS_RESOLVED, 0),
        "rejected": counts.get(Complaint.STATUS_REJECTED, 0),
        "withdrawn": counts.get(Complaint.STATUS_WITHDRAWN, 0),
    }


def by_category(criteria=()):
    rows = (db.session.query(Complaint.category, func.count(Complaint.id))
            .filter(*criteria).group_by(Complaint.category).order_by(func.count(Complaint.id).desc()).all())
    return {"labels": [r[0] for r in rows], "values": [r[1] for r in rows]}


def by_department():
    rows = (db.session.query(Department.name, func.count(Complaint.id))
            .join(Complaint, Complaint.department_id == Department.id)
            .group_by(Department.name).order_by(func.count(Complaint.id).desc()).all())
    return {"labels": [r[0] for r in rows], "values": [r[1] for r in rows]}


def monthly_trend(criteria=(), months=6):
    """Bucketed in Python so it works on SQLite and PostgreSQL alike."""
    today = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    keys = []
    y, m = today.year, today.month
    for _ in range(months):
        keys.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    keys.reverse()
    start = datetime(keys[0][0], keys[0][1], 1)
    buckets = OrderedDict((k, 0) for k in keys)
    for (created,) in db.session.query(Complaint.created_at).filter(Complaint.created_at >= start, *criteria):
        k = (created.year, created.month)
        if k in buckets:
            buckets[k] += 1
    return {"labels": [datetime(y, m, 1).strftime("%b %Y") for y, m in buckets],
            "values": list(buckets.values())}


def avg_resolution_days(criteria=()):
    """Average days from submission to resolution; None when there is no data yet."""
    rows = (db.session.query(Complaint.created_at, Complaint.resolved_at)
            .filter(Complaint.resolved_at.isnot(None), *criteria).all())
    if not rows:
        return None
    total = sum((r - c).total_seconds() for c, r in rows)
    return round(total / len(rows) / 86400, 1)


def resolution_by_department():
    out = {"labels": [], "values": []}
    for dept in Department.query.order_by(Department.name):
        avg = avg_resolution_days([Complaint.department_id == dept.id])
        if avg is not None:
            out["labels"].append(dept.name)
            out["values"].append(avg)
    return out


def platform_counts():
    return {"citizens": User.query.filter_by(role=User.ROLE_CITIZEN).count(),
            "complaints": Complaint.query.count(),
            "resolved": Complaint.query.filter_by(status=Complaint.STATUS_RESOLVED).count()}
