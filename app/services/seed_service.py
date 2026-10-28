"""Reference data (departments/categories) and clearly-labelled DEMO data."""
import random
from datetime import timedelta
from ..extensions import db
from ..models import Department, Category, User, Complaint, ComplaintUpdate
from ..models.user import utcnow
from . import complaint_service as cs

DEPARTMENTS = [
    ("Roads & Public Works", "Potholes, damaged roads and footpaths", "roads@example.gov"),
    ("Sanitation & Waste", "Garbage collection and cleanliness", "sanitation@example.gov"),
    ("Water & Drainage", "Water supply, leakage and drainage", "water@example.gov"),
    ("Electricity & Street Lighting", "Streetlights and public power", "lights@example.gov"),
    ("Parks & Public Spaces", "Parks, trees and public amenities", "parks@example.gov"),
]
CATEGORIES = [
    ("Pothole", "construction"), ("Garbage", "trash-2"), ("Damaged Road", "route"),
    ("Broken Streetlight", "lightbulb"), ("Water Leakage", "droplets"),
    ("Drainage Problem", "waves"), ("Other", "alert-circle"),
]
DEMO_PASSWORD = "Demo@12345"


def ensure_reference_data():
    for name, desc, email in DEPARTMENTS:
        if not Department.query.filter_by(name=name).first():
            db.session.add(Department(name=name, description=desc, contact_email=email))
    for name, icon in CATEGORIES:
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name, icon=icon))
    db.session.commit()


def _user(name, email, role, dept=None):
    u = User.query.filter_by(email=email).first()
    if not u:
        u = User(full_name=name, email=email, role=role, department_id=dept.id if dept else None)
        u.set_password(DEMO_PASSWORD)
        db.session.add(u)
        db.session.flush()
    return u


def seed_demo_data():
    ensure_reference_data()
    depts = Department.query.order_by(Department.id).all()
    admin = _user("Demo Admin", "admin@demo.civicconnect.local", "admin")
    officers = [_user(f"Demo Officer ({d.name.split()[0]})", f"officer{i}@demo.civicconnect.local",
                      "authority", d) for i, d in enumerate(depts, 1)]
    citizen = _user("Demo Citizen", "citizen@demo.civicconnect.local", "citizen")
    db.session.commit()
    if Complaint.query.filter_by(user_id=citizen.id).count():
        print("Demo complaints already exist; skipping.")
        return
    samples = [("Deep pothole near school gate", "Pothole", 0), ("Overflowing garbage bins", "Garbage", 1),
               ("Water pipe leaking on main road", "Water Leakage", 2), ("Streetlight not working", "Broken Streetlight", 3),
               ("Blocked storm drain", "Drainage Problem", 2), ("Cracked road surface", "Damaged Road", 0)]
    random.seed(1)
    for i, (title, cat, di) in enumerate(samples):
        c = cs.create_complaint(citizen, {
            "title": f"[DEMO] {title}", "category": cat, "description": "Demo complaint created by the seed script.",
            "address": "Demo Street, Sample City", "latitude": 28.61 + random.uniform(-0.03, 0.03),
            "longitude": 77.21 + random.uniform(-0.03, 0.03)})
        c.created_at = utcnow() - timedelta(days=random.randint(1, 120))
        if i >= 1:
            cs.assign(c, admin, depts[di].id, officers[di].id, random.choice(Complaint.PRIORITIES))
        if i >= 2:
            cs.accept(c, officers[di])
        if i >= 4:
            cs.submit_resolution(c, officers[di], "Demo: issue repaired by field team.")
            c.resolved_at = c.created_at + timedelta(days=random.randint(2, 15))
        db.session.commit()
    print(f"Demo accounts (password: {DEMO_PASSWORD}): admin@, officer1@..officer5@, citizen@demo.civicconnect.local")
