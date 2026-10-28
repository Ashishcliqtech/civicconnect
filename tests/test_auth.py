from app.models import User, Notification
from app.extensions import db


def test_register_and_login(client):
    r = client.post("/auth/register", data={"full_name": "Asha Rao", "email": "asha@test.local",
                    "password": "Secret123", "confirm": "Secret123"})
    assert r.status_code == 302
    u = User.query.filter_by(email="asha@test.local").first()
    assert u.role == "citizen" and u.password_hash != "Secret123"  # hashed, citizen only
    r = client.post("/auth/login", data={"email": "asha@test.local", "password": "Secret123"})
    assert r.status_code == 302 and "/citizen/dashboard" in r.headers["Location"]


def test_duplicate_email_rejected(client, citizen):
    r = client.post("/auth/register", data={"full_name": "Dup", "email": citizen.email,
                    "password": "Secret123", "confirm": "Secret123"})
    assert r.status_code == 200 and b"already exists" in r.data
    assert User.query.filter_by(email=citizen.email).count() == 1


def test_weak_password_rejected(client):
    r = client.post("/auth/register", data={"full_name": "Weak", "email": "w@test.local",
                    "password": "short", "confirm": "short"})
    assert r.status_code == 200 and User.query.filter_by(email="w@test.local").first() is None


def test_invalid_credentials(client, citizen):
    r = client.post("/auth/login", data={"email": citizen.email, "password": "wrong"})
    assert r.status_code == 200 and b"Invalid email or password" in r.data


def test_inactive_user_cannot_login(client, make_user):
    u = make_user("citizen", active=False)
    r = client.post("/auth/login", data={"email": u.email, "password": "Passw0rd!"})
    assert r.status_code == 200 and b"Invalid email or password" in r.data


def test_dashboards_require_login(client):
    for url in ("/citizen/dashboard", "/authority/dashboard", "/admin/dashboard"):
        r = client.get(url)
        assert r.status_code == 302 and "/auth/login" in r.headers["Location"]


def test_role_restrictions(client, login, citizen, officer, admin):
    login(client, citizen)
    assert client.get("/admin/dashboard").status_code == 403
    assert client.get("/authority/dashboard").status_code == 403
    client.post("/auth/logout")
    login(client, officer)
    assert client.get("/admin/users").status_code == 403
    assert client.get("/citizen/dashboard").status_code == 403
    client.post("/auth/logout")
    login(client, admin)
    assert client.get("/admin/dashboard").status_code == 200


def test_logout_requires_post(client, login, citizen):
    login(client, citizen)
    assert client.get("/auth/logout").status_code == 405
    assert client.post("/auth/logout").status_code == 302
    assert client.get("/citizen/dashboard").status_code == 302


def test_open_redirect_blocked(client, citizen):
    r = client.post("/auth/login?next=https://evil.example", data={"email": citizen.email, "password": "Passw0rd!"})
    assert "evil.example" not in r.headers["Location"]


def test_notification_list_pagination(client, login, citizen):
    for i in range(16):
        db.session.add(Notification(user_id=citizen.id, title=f"Notice {i}", message="Test notification"))
    db.session.commit()
    login(client, citizen)
    response = client.get("/auth/notifications?page=2")
    assert response.status_code == 200
    assert b"Page 2 of 2" in response.data


def test_public_pages_and_errors(client):
    for url in ("/", "/about", "/public-complaints", "/auth/login", "/auth/register"):
        assert client.get(url).status_code == 200
    assert client.get("/does-not-exist").status_code == 404
