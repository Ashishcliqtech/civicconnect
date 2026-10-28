import io
from app.models import Complaint, Notification

FORM = {"title": "Broken streetlight", "category": "Broken Streetlight", "address": "Park Road",
        "description": "The streetlight has been broken for a week now.", "latitude": "28.6", "longitude": "77.2"}


def test_citizen_can_submit_complaint(client, login, citizen):
    login(client, citizen)
    r = client.post("/citizen/submit", data=FORM)
    assert r.status_code == 302
    c = Complaint.query.one()
    assert c.reference_number.startswith("CC-") and c.status == "Submitted" and c.user_id == citizen.id
    assert Notification.query.filter_by(user_id=citizen.id).count() == 1  # submission notification


def test_submit_validation(client, login, citizen):
    login(client, citizen)
    bad = dict(FORM, title="abc", latitude="999")
    r = client.post("/citizen/submit", data=bad)
    assert r.status_code == 200 and Complaint.query.count() == 0
    r = client.post("/citizen/submit", data=dict(FORM, category="Not A Category"))
    assert Complaint.query.count() == 0


def test_citizen_dashboard_and_list(client, login, citizen, make_complaint):
    make_complaint(citizen)
    login(client, citizen)
    assert client.get("/citizen/dashboard").status_code == 200
    r = client.get("/citizen/complaints?status=Submitted")
    assert b"Big pothole" in r.data


def test_complaint_list_pagination(client, login, citizen, make_complaint):
    for i in range(16):
        make_complaint(citizen, title=f"Complaint {i}")
    login(client, citizen)
    response = client.get("/citizen/complaints?page=2")
    assert response.status_code == 200
    assert b"Page 2 of 2" in response.data


def test_citizen_cannot_view_others_complaint(client, login, make_user, make_complaint, citizen):
    other = make_user("citizen", email="other@test.local")
    c = make_complaint(other)
    login(client, citizen)
    assert client.get(f"/citizen/complaints/{c.id}").status_code == 403
    assert client.post(f"/citizen/complaints/{c.id}/withdraw").status_code == 403


def test_edit_only_while_submitted(client, login, citizen, make_complaint, admin, depts):
    from app.services import complaint_service as cs
    c = make_complaint(citizen)
    login(client, citizen)
    assert client.post(f"/citizen/complaints/{c.id}/edit", data=dict(FORM, title="Updated title")).status_code == 302
    assert Complaint.query.get(c.id).title == "Updated title"
    cs.assign(c, admin, depts[0].id)
    r = client.get(f"/citizen/complaints/{c.id}/edit")
    assert r.status_code == 302  # no longer editable


def test_withdraw_rules(client, login, citizen, make_complaint):
    c = make_complaint(citizen)
    login(client, citizen)
    client.post(f"/citizen/complaints/{c.id}/withdraw")
    assert Complaint.query.get(c.id).status == "Withdrawn"
    client.post(f"/citizen/complaints/{c.id}/withdraw")  # second time is refused, no crash
    assert Complaint.query.get(c.id).status == "Withdrawn"


def test_public_listing_hides_private_data(client, citizen, make_complaint):
    make_complaint(citizen, latitude=28.612345, longitude=77.209876)
    data = client.get("/api/public/complaints").get_json()
    assert len(data) == 1
    item = data[0]
    assert "email" not in str(item) and citizen.email not in client.get("/public-complaints").get_data(as_text=True)
    assert item["lat"] == 28.612 and item["lng"] == 77.21  # rounded
