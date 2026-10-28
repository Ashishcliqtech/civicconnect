import pytest
from app.models import Complaint, User, AuditLog, Notification, Resolution
from app.services import complaint_service as cs
from app.services.complaint_service import ServiceError


def test_assign_department(client, login, admin, citizen, make_complaint, depts, officer):
    c = make_complaint(citizen)
    login(client, admin)
    r = client.post(f"/admin/complaints/{c.id}/assign",
                    data={"department_id": depts[0].id, "officer_id": officer.id, "priority": "High"})
    assert r.status_code == 302
    c = Complaint.query.get(c.id)
    assert c.department_id == depts[0].id and c.assigned_officer_id == officer.id
    assert c.status == "Assigned" and c.priority == "High"
    assert Notification.query.filter_by(user_id=officer.id).count() == 1
    assert Notification.query.filter_by(user_id=citizen.id).filter(Notification.title.like("Status updated%")).count() == 1
    assert AuditLog.query.filter_by(action="complaint_assigned").count() == 1


def test_officer_must_belong_to_department(admin, citizen, make_complaint, depts, officer):
    c = make_complaint(citizen)
    with pytest.raises(ServiceError):
        cs.assign(c, admin, depts[1].id, officer.id)  # officer is in dept 0


def test_non_admin_cannot_assign_via_route(client, login, citizen, officer, make_complaint, depts):
    c = make_complaint(citizen)
    login(client, officer)
    assert client.post(f"/admin/complaints/{c.id}/assign", data={"department_id": depts[0].id, "priority": "Low"}).status_code == 403
    assert Complaint.query.get(c.id).department_id is None


def test_verify_and_reopen(client, login, admin, citizen, officer, make_complaint, depts):
    c = make_complaint(citizen)
    cs.assign(c, admin, depts[0].id, officer.id)
    cs.accept(c, officer)
    res = cs.submit_resolution(c, officer, "Repaired the road surface.")
    login(client, admin)
    client.post(f"/admin/resolutions/{res.id}/verify")
    assert Resolution.query.get(res.id).verified_at is not None
    assert Resolution.query.get(res.id).verified_by_admin_id == admin.id
    client.post(f"/admin/complaints/{c.id}/reopen", data={"reason": ""})
    assert Complaint.query.get(c.id).status == "Resolved"  # reason required
    client.post(f"/admin/complaints/{c.id}/reopen", data={"reason": "Pothole is back"})
    c = Complaint.query.get(c.id)
    assert c.status == "Under Review" and c.resolved_at is None
    assert AuditLog.query.filter_by(action="complaint_reopened").count() == 1


def test_admin_user_management(client, login, admin, depts):
    login(client, admin)
    r = client.post("/admin/users/new", data={"full_name": "New Officer", "email": "off@test.local", "role": "authority",
                    "department_id": depts[1].id, "password": "Officer123", "is_active": "y"})
    assert r.status_code == 302
    u = User.query.filter_by(email="off@test.local").first()
    assert u.role == "authority" and u.department_id == depts[1].id
    users_page = client.get("/admin/users?q=off%40test.local")
    assert users_page.status_code == 200
    assert b"off@test.local" in users_page.data
    r = client.post(f"/admin/users/{u.id}/edit", data={"full_name": "New Officer", "email": "off@test.local",
                    "role": "authority", "department_id": depts[1].id})  # is_active omitted => deactivated
    assert User.query.get(u.id).is_active is False


def test_admin_user_list_pagination(client, login, admin, make_user):
    for i in range(16):
        make_user(email=f"user{i}@test.local")
    login(client, admin)
    response = client.get("/admin/users?page=2")
    assert response.status_code == 200
    assert b"Page 2 of 2" in response.data


def test_admin_cannot_demote_self(client, login, admin):
    login(client, admin)
    client.post(f"/admin/users/{admin.id}/edit", data={"full_name": "Me", "email": admin.email, "role": "citizen",
                "department_id": 0, "is_active": "y"})
    assert User.query.get(admin.id).role == "admin"


def test_department_category_and_reports_pages(client, login, admin, depts):
    login(client, admin)
    assert client.post("/admin/departments", data={"name": "Fire Safety", "description": "x", "is_active": "y"}).status_code == 302
    assert client.post("/admin/categories", data={"name": "Fallen Tree", "icon": "trees"}).status_code == 302
    client.post(f"/admin/departments/{depts[0].id}/toggle")
    for url in ("/admin/departments", "/admin/categories", "/admin/reports", "/admin/audit-log",
                "/admin/complaints", "/admin/reports/export.csv", "/admin/dashboard"):
        assert client.get(url).status_code == 200, url


def test_closed_complaint_cannot_be_assigned(admin, citizen, make_complaint, depts):
    c = make_complaint(citizen)
    cs.reject(c, admin, "Spam")
    with pytest.raises(ServiceError):
        cs.assign(c, admin, depts[0].id)
