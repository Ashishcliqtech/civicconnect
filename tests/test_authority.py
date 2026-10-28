import pytest
from app.models import Complaint, Notification, Resolution
from app.services import complaint_service as cs
from app.services.complaint_service import ServiceError


@pytest.fixture
def assigned(admin, citizen, make_complaint, depts, officer):
    c = make_complaint(citizen)
    cs.assign(c, admin, depts[0].id, officer.id, "High")
    return c


def test_officer_sees_only_own_department(client, login, officer, admin, citizen, make_complaint, depts, assigned):
    other = make_complaint(citizen, title="Garbage in other dept", category="Garbage")
    cs.assign(other, admin, depts[1].id)
    login(client, officer)
    page = client.get("/authority/complaints").get_data(as_text=True)
    assert assigned.reference_number in page and other.reference_number not in page
    assert client.get(f"/authority/complaints/{other.id}").status_code == 403
    assert client.post(f"/authority/complaints/{other.id}/accept").status_code == 403
    assert client.get(f"/authority/complaints/{assigned.id}").status_code == 200


def test_accept_then_resolve_flow(client, login, officer, citizen, assigned, png):
    login(client, officer)
    client.post(f"/authority/complaints/{assigned.id}/accept")
    assert Complaint.query.get(assigned.id).status == "In Progress"
    r = client.post(f"/authority/complaints/{assigned.id}/resolve",
                    data={"action_taken": "Filled the pothole with asphalt.", "proof": (png(), "proof.png")},
                    content_type="multipart/form-data")
    assert r.status_code == 302
    c = Complaint.query.get(assigned.id)
    assert c.status == "Resolved" and c.resolved_at is not None
    res = Resolution.query.one()
    assert res.proof_photo_filename and res.verified_at is None
    assert Notification.query.filter_by(user_id=citizen.id, title="Resolution evidence submitted").count() == 1


def test_cannot_resolve_without_accepting(officer, assigned):
    with pytest.raises(ServiceError):
        cs.submit_resolution(assigned, officer, "Done")


def test_reject_needs_reason(client, login, officer, assigned):
    login(client, officer)
    client.post(f"/authority/complaints/{assigned.id}/reject", data={"reason": ""})
    assert Complaint.query.get(assigned.id).status == "Assigned"
    client.post(f"/authority/complaints/{assigned.id}/reject", data={"reason": "Not under our jurisdiction"})
    assert Complaint.query.get(assigned.id).status == "Rejected"


def test_internal_notes_hidden_from_citizen(client, login, officer, citizen, assigned):
    login(client, officer)
    client.post(f"/authority/complaints/{assigned.id}/note", data={"message": "SECRET-INTERNAL-NOTE"})
    assert b"SECRET-INTERNAL-NOTE" in client.get(f"/authority/complaints/{assigned.id}").data
    client.post("/auth/logout")
    login(client, citizen)
    assert b"SECRET-INTERNAL-NOTE" not in client.get(f"/citizen/complaints/{assigned.id}").data


def test_officer_cannot_reopen_or_assign(officer, assigned):
    cs.reject(assigned, officer, "Invalid report")
    with pytest.raises(ServiceError):
        cs.update_status(assigned, "Under Review", officer)
    with pytest.raises(ServiceError):
        cs.assign(assigned, officer, 1)


def test_request_info_notifies_citizen(officer, citizen, assigned):
    cs.request_info(assigned, officer, "Please share the nearest landmark.")
    assert Notification.query.filter_by(user_id=citizen.id).filter(Notification.title.like("More information%")).count() == 1


def test_authority_dashboard(client, login, officer, assigned):
    login(client, officer)
    assert client.get("/authority/dashboard").status_code == 200
