"""Test fixtures: every test gets a fresh temporary database and its own upload folder."""
import io
import pytest
from PIL import Image
from app import create_app
from app.extensions import db
from app.models import User, Department
from app.services import seed_service, complaint_service as cs
from config import TestingConfig


@pytest.fixture
def app(tmp_path):
    class Cfg(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'test.db'}"
        UPLOAD_FOLDER = str(tmp_path / "uploads")
        DATA_DIR = tmp_path
    app = create_app(Cfg)
    with app.app_context():
        db.create_all()
        seed_service.ensure_reference_data()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


PASSWORD = "Passw0rd!"


@pytest.fixture
def make_user(app):
    def _make(role="citizen", email=None, dept=None, active=True):
        email = email or f"{role}{User.query.count()}@test.local"
        u = User(full_name=f"Test {role.title()}", email=email, role=role, is_active=active,
                 department_id=dept.id if dept else None)
        u.set_password(PASSWORD)
        db.session.add(u)
        db.session.commit()
        return u
    return _make


@pytest.fixture
def login():
    def _login(client, user, password=PASSWORD):
        return client.post("/auth/login", data={"email": user.email, "password": password})
    return _login


@pytest.fixture
def depts(app):
    return Department.query.order_by(Department.id).all()


@pytest.fixture
def citizen(make_user):
    return make_user("citizen")


@pytest.fixture
def admin(make_user):
    return make_user("admin")


@pytest.fixture
def officer(make_user, depts):
    return make_user("authority", dept=depts[0])


@pytest.fixture
def make_complaint(app):
    def _make(user, **over):
        data = {"title": "Big pothole on Main St", "category": "Pothole",
                "description": "A very large pothole that damages vehicles.",
                "address": "Main Street", "latitude": 28.61, "longitude": 77.2}
        data.update(over)
        return cs.create_complaint(user, data)
    return _make


def png_bytes(size=(40, 40)):
    buf = io.BytesIO()
    Image.new("RGB", size, "red").save(buf, "PNG")
    buf.seek(0)
    return buf


@pytest.fixture
def png():
    return png_bytes
