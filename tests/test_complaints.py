import pytest
from app.models import Complaint, Notification, ComplaintUpdate
from app.services import complaint_service as cs
from app.services.complaint_service import ServiceError


def test_reference_numbers_unique_and_readable(citizen, make_complaint):
    refs = {make_complaint(citizen).reference_number for _ in range(5)}
    assert len(refs) == 5 and all(r.startswith("CC-") for r in refs)


def test_transition_table():
    assert cs.can_transition("Submitted", "Under Review")
    assert cs.can_transition("In Progress", "Resolved")
    assert not cs.can_transition("Submitted", "Resolved")
    assert not cs.can_transition("Withdrawn", "Under Review")
    assert not cs.can_transition("Resolved", "In Progress")


def test_citizen_cannot_change_status_or_resolve(citizen, make_complaint):
    c = make_complaint(citizen)
    for target in ("Resolved", "Under Review", "In Progress"):
        with pytest.raises(ServiceError):
            cs.update_status(c, target, citizen)
    assert c.status == "Submitted"


def test_invalid_transition_rejected(admin, citizen, make_complaint):
    c = make_complaint(citizen)
    with pytest.raises(ServiceError):
        cs.update_status(c, "In Progress", admin)  # Submitted -> In Progress is not allowed
    with pytest.raises(ServiceError):
        cs.update_status(c, "Resolved", admin)  # resolved only via resolution form


def test_status_change_creates_timeline_and_notification(admin, citizen, make_complaint):
    c = make_complaint(citizen)
    cs.update_status(c, "Under Review", admin, "Looking into it")
    assert c.status == "Under Review"
    assert ComplaintUpdate.query.filter_by(complaint_id=c.id, new_status="Under Review").count() == 1
    assert any("Under Review" in n.message for n in Notification.query.filter_by(user_id=citizen.id))


def test_reject_requires_reason(admin, citizen, make_complaint):
    c = make_complaint(citizen)
    with pytest.raises(ServiceError):
        cs.reject(c, admin, "  ")
    cs.reject(c, admin, "Duplicate of CC-2025-AAAAAA")
    assert c.status == "Rejected"


def test_filtering_and_sorting(app, citizen, make_complaint):
    from werkzeug.datastructures import MultiDict
    make_complaint(citizen, category="Garbage", title="Garbage pile near school")
    make_complaint(citizen, category="Pothole")
    q = cs.filter_complaints(Complaint.query, MultiDict({"category": "Garbage"}))
    assert q.count() == 1
    q = cs.filter_complaints(Complaint.query, MultiDict({"q": "school"}))
    assert q.count() == 1
    assert cs.filter_complaints(Complaint.query, MultiDict({"sort": "priority"})).count() == 2
