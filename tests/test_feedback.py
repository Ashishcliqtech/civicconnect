import pytest
from app.models import Feedback
from app.services import complaint_service as cs
from app.services.complaint_service import ServiceError


@pytest.fixture
def resolved(admin, citizen, officer, make_complaint, depts):
    c = make_complaint(citizen)
    cs.assign(c, admin, depts[0].id, officer.id)
    cs.accept(c, officer)
    cs.submit_resolution(c, officer, "Fixed the issue properly.")
    return c


def test_feedback_after_resolution(client, login, citizen, resolved):
    login(client, citizen)
    r = client.post(f"/citizen/complaints/{resolved.id}/feedback", data={"rating": 5, "comments": "Great work"})
    assert r.status_code == 302
    fb = Feedback.query.one()
    assert fb.rating == 5 and fb.user_id == citizen.id


def test_only_one_feedback(citizen, resolved):
    cs.add_feedback(resolved, citizen, 4, "ok")
    with pytest.raises(ServiceError):
        cs.add_feedback(resolved, citizen, 5, "again")


def test_feedback_requires_resolved(citizen, make_complaint):
    c = make_complaint(citizen)
    with pytest.raises(ServiceError):
        cs.add_feedback(c, citizen, 5, "")


def test_only_owner_can_give_feedback(make_user, resolved):
    other = make_user("citizen", email="o@test.local")
    with pytest.raises(ServiceError):
        cs.add_feedback(resolved, other, 3, "")


def test_rating_range_validated(client, login, citizen, resolved):
    login(client, citizen)
    client.post(f"/citizen/complaints/{resolved.id}/feedback", data={"rating": 9})
    assert Feedback.query.count() == 0
