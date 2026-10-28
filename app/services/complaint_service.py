"""All complaint business rules live here so routes stay thin and rules are not duplicated."""
import secrets
from sqlalchemy import or_, case
from ..extensions import db
from ..models import (Complaint, ComplaintUpdate, Resolution, Feedback, User, Department)
from ..models.user import utcnow
from . import audit_service, notification_service as ns

S = Complaint


class ServiceError(Exception):
    """Raised when a business rule is violated; routes show it as a flash message."""


# ---- Status-transition policy ------------------------------------------------
TRANSITIONS = {
    S.STATUS_SUBMITTED: {S.STATUS_REVIEW, S.STATUS_ASSIGNED, S.STATUS_REJECTED, S.STATUS_WITHDRAWN},
    S.STATUS_REVIEW: {S.STATUS_ASSIGNED, S.STATUS_PROGRESS, S.STATUS_REJECTED, S.STATUS_WITHDRAWN},
    S.STATUS_ASSIGNED: {S.STATUS_REVIEW, S.STATUS_PROGRESS, S.STATUS_REJECTED},
    S.STATUS_PROGRESS: {S.STATUS_RESOLVED, S.STATUS_REVIEW},
    S.STATUS_RESOLVED: {S.STATUS_REVIEW},   # reopen (admin only)
    S.STATUS_REJECTED: {S.STATUS_REVIEW},   # reopen (admin only)
    S.STATUS_WITHDRAWN: set(),              # final
}
CITIZEN_WITHDRAWABLE = {S.STATUS_SUBMITTED, S.STATUS_REVIEW}


def can_transition(old, new):
    return new in TRANSITIONS.get(old, set())


def allowed_manual_targets(complaint, actor):
    """Statuses the actor may pick in the 'update status' form (Resolved/Withdrawn/reopen have own flows)."""
    if actor.is_citizen or complaint.status in (S.STATUS_RESOLVED, S.STATUS_REJECTED, S.STATUS_WITHDRAWN):
        return []
    targets = TRANSITIONS[complaint.status] - {S.STATUS_RESOLVED, S.STATUS_WITHDRAWN}
    if actor.is_authority:  # officers cannot assign; admins do that
        targets -= {S.STATUS_ASSIGNED}
    return sorted(targets)


# ---- Helpers -----------------------------------------------------------------
def _check_access(actor, complaint):
    from ..utils.helpers import user_can_access_complaint
    if not user_can_access_complaint(actor, complaint):
        raise ServiceError("You do not have access to this complaint.")


def _apply_status(complaint, new_status, actor, message, visibility="public"):
    old = complaint.status
    if not can_transition(old, new_status):
        raise ServiceError(f"Invalid status change: {old} → {new_status}.")
    complaint.status = new_status
    complaint.updated_at = utcnow()
    db.session.add(ComplaintUpdate(complaint=complaint, actor_id=actor.id, old_status=old,
                                   new_status=new_status, message=message, visibility=visibility))
    audit_service.log_action(actor, "status_change", "complaint", complaint.id, f"{old} -> {new_status}")
    ns.notify(complaint.user_id, f"Status updated: {complaint.reference_number}",
              f"Your complaint is now '{new_status}'." + (f" {message}" if message else ""), complaint.id)


def generate_reference():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no confusing 0/O/1/I
    year = utcnow().year
    while True:
        ref = f"CC-{year}-" + "".join(secrets.choice(alphabet) for _ in range(6))
        if not Complaint.query.filter_by(reference_number=ref).first():
            return ref


# ---- Citizen workflows -------------------------------------------------------
def create_complaint(user, data, photo_filename=None):
    complaint = Complaint(reference_number=generate_reference(), user_id=user.id,
                          title=data["title"].strip(), description=data["description"].strip(),
                          category=data["category"], address=data["address"].strip(),
                          latitude=data["latitude"], longitude=data["longitude"],
                          photo_filename=photo_filename, priority="Medium")
    db.session.add(complaint)
    db.session.flush()
    db.session.add(ComplaintUpdate(complaint=complaint, actor_id=user.id, new_status=S.STATUS_SUBMITTED,
                                   message="Complaint submitted.", visibility="public"))
    ns.notify(user.id, "Complaint submitted",
              f"Your complaint {complaint.reference_number} was received.", complaint.id)
    audit_service.log_action(user, "complaint_created", "complaint", complaint.id, complaint.reference_number)
    db.session.commit()
    return complaint


def update_complaint(complaint, actor, data, new_photo=None):
    if complaint.user_id != actor.id:
        raise ServiceError("You can only edit your own complaints.")
    if complaint.status != S.STATUS_SUBMITTED:
        raise ServiceError("A complaint can only be edited while it is still 'Submitted'.")
    for field in ("title", "description", "category", "address", "latitude", "longitude"):
        setattr(complaint, field, data[field].strip() if isinstance(data[field], str) else data[field])
    if new_photo:
        complaint.photo_filename = new_photo
    db.session.add(ComplaintUpdate(complaint=complaint, actor_id=actor.id,
                                   message="Complaint details edited by citizen.", visibility="public"))
    db.session.commit()


def withdraw(complaint, actor):
    if complaint.user_id != actor.id:
        raise ServiceError("You can only withdraw your own complaints.")
    if complaint.status not in CITIZEN_WITHDRAWABLE:
        raise ServiceError("This complaint can no longer be withdrawn.")
    _apply_status(complaint, S.STATUS_WITHDRAWN, actor, "Withdrawn by citizen.")
    ns.notify_department(complaint.department_id, "Complaint withdrawn",
                         f"{complaint.reference_number} was withdrawn by the citizen.", complaint.id)
    db.session.commit()


def add_citizen_comment(complaint, actor, message):
    if complaint.user_id != actor.id:
        raise ServiceError("You can only comment on your own complaints.")
    if not complaint.is_open:
        raise ServiceError("This complaint is closed.")
    db.session.add(ComplaintUpdate(complaint=complaint, actor_id=actor.id, message=message.strip(),
                                   visibility="public"))
    ns.notify_department(complaint.department_id, "Citizen replied",
                         f"New message on {complaint.reference_number}.", complaint.id)
    db.session.commit()


def add_feedback(complaint, actor, rating, comments):
    if complaint.user_id != actor.id:
        raise ServiceError("Only the complaint owner can leave feedback.")
    if complaint.status != S.STATUS_RESOLVED:
        raise ServiceError("Feedback is only possible after a complaint is resolved.")
    if complaint.feedback is not None:
        raise ServiceError("Feedback was already submitted for this complaint.")
    if not 1 <= int(rating) <= 5:
        raise ServiceError("Rating must be between 1 and 5.")
    db.session.add(Feedback(complaint_id=complaint.id, user_id=actor.id, rating=int(rating),
                            comments=(comments or "").strip()))
    audit_service.log_action(actor, "feedback_submitted", "complaint", complaint.id, f"rating={rating}")
    db.session.commit()


# ---- Authority / admin workflows --------------------------------------------
def update_status(complaint, new_status, actor, message=""):
    if actor.is_citizen:
        raise ServiceError("Citizens cannot change complaint status.")
    _check_access(actor, complaint)
    if new_status == S.STATUS_RESOLVED:
        raise ServiceError("Use the resolution form to mark a complaint as resolved.")
    if new_status == S.STATUS_WITHDRAWN:
        raise ServiceError("Only the citizen can withdraw a complaint.")
    if complaint.status in (S.STATUS_RESOLVED, S.STATUS_REJECTED) and not actor.is_admin:
        raise ServiceError("Only an administrator can reopen a closed complaint.")
    if new_status == S.STATUS_ASSIGNED and not actor.is_admin:
        raise ServiceError("Only an administrator can assign complaints.")
    if new_status == S.STATUS_REJECTED and not (message or "").strip():
        raise ServiceError("A reason is required to reject a complaint.")
    _apply_status(complaint, new_status, actor, (message or "").strip())
    db.session.commit()


def accept(complaint, actor):
    update_status(complaint, S.STATUS_PROGRESS, actor, "Complaint accepted; work is starting.")


def reject(complaint, actor, reason):
    update_status(complaint, S.STATUS_REJECTED, actor, reason)


def assign(complaint, actor, department_id, officer_id=None, priority=None):
    if not actor.is_admin:
        raise ServiceError("Only administrators can assign complaints.")
    if not complaint.is_open:
        raise ServiceError("Closed complaints cannot be assigned. Reopen it first.")
    dept = db.session.get(Department, department_id)
    if dept is None or not dept.is_active:
        raise ServiceError("Select a valid, active department.")
    officer = None
    if officer_id:
        officer = db.session.get(User, officer_id)
        if not officer or officer.role != User.ROLE_AUTHORITY or officer.department_id != dept.id:
            raise ServiceError("That officer does not belong to the selected department.")
    if priority:
        if priority not in Complaint.PRIORITIES:
            raise ServiceError("Invalid priority.")
        complaint.priority = priority
    complaint.department_id = dept.id
    complaint.assigned_officer_id = officer.id if officer else None
    msg = f"Assigned to {dept.name}" + (f" (officer: {officer.full_name})" if officer else "") + "."
    if complaint.status in (S.STATUS_SUBMITTED, S.STATUS_REVIEW):
        _apply_status(complaint, S.STATUS_ASSIGNED, actor, msg)
    else:  # reassignment while Assigned / In Progress: no status change
        db.session.add(ComplaintUpdate(complaint=complaint, actor_id=actor.id, message=msg))
        ns.notify(complaint.user_id, f"Complaint reassigned: {complaint.reference_number}", msg, complaint.id)
    audit_service.log_action(actor, "complaint_assigned", "complaint", complaint.id, msg)
    if officer:
        ns.notify(officer.id, "New complaint assigned", f"{complaint.reference_number} was assigned to you.", complaint.id)
    else:
        ns.notify_department(dept.id, "New complaint assigned",
                             f"{complaint.reference_number} was assigned to {dept.name}.", complaint.id)
    db.session.commit()


def add_note(complaint, actor, message, visibility="internal"):
    if actor.is_citizen:
        raise ServiceError("Not allowed.")
    _check_access(actor, complaint)
    if visibility not in ("internal", "public"):
        raise ServiceError("Invalid visibility.")
    if not (message or "").strip():
        raise ServiceError("Note cannot be empty.")
    db.session.add(ComplaintUpdate(complaint=complaint, actor_id=actor.id, message=message.strip(),
                                   visibility=visibility))
    db.session.commit()


def request_info(complaint, actor, message):
    if actor.is_citizen:
        raise ServiceError("Not allowed.")
    _check_access(actor, complaint)
    if not complaint.is_open:
        raise ServiceError("This complaint is closed.")
    text = f"Additional information requested: {message.strip()}"
    db.session.add(ComplaintUpdate(complaint=complaint, actor_id=actor.id, message=text, visibility="public"))
    ns.notify(complaint.user_id, f"More information needed: {complaint.reference_number}", message.strip(), complaint.id)
    db.session.commit()


def submit_resolution(complaint, actor, action_taken, proof_filename=None):
    if actor.is_citizen:
        raise ServiceError("Not allowed.")
    _check_access(actor, complaint)
    if complaint.status != S.STATUS_PROGRESS:
        raise ServiceError("Only complaints that are 'In Progress' can be resolved. Accept it first.")
    if not (action_taken or "").strip():
        raise ServiceError("Describe the action taken.")
    res = Resolution(complaint_id=complaint.id, officer_id=actor.id, action_taken=action_taken.strip(),
                     proof_photo_filename=proof_filename)
    db.session.add(res)
    _apply_status(complaint, S.STATUS_RESOLVED, actor, f"Resolved: {action_taken.strip()}")
    complaint.resolved_at = utcnow()
    ns.notify(complaint.user_id, "Resolution evidence submitted",
              f"Evidence for {complaint.reference_number} was submitted. Please review it.", complaint.id)
    for admin in User.query.filter_by(role=User.ROLE_ADMIN, is_active=True):
        ns.notify(admin.id, "Resolution awaiting verification", complaint.reference_number, complaint.id)
    db.session.commit()
    return res


def verify_resolution(resolution, actor):
    if not actor.is_admin:
        raise ServiceError("Only administrators can verify resolutions.")
    if resolution.complaint.status != S.STATUS_RESOLVED:
        raise ServiceError("This complaint is no longer resolved.")
    if resolution.verified_at:
        raise ServiceError("Already verified.")
    resolution.verified_by_admin_id = actor.id
    resolution.verified_at = utcnow()
    c = resolution.complaint
    db.session.add(ComplaintUpdate(complaint=c, actor_id=actor.id, message="Resolution verified by administrator."))
    ns.notify(c.user_id, "Resolution verified", f"The fix for {c.reference_number} was verified.", c.id)
    audit_service.log_action(actor, "resolution_verified", "complaint", c.id)
    db.session.commit()


def reopen(complaint, actor, reason):
    if not actor.is_admin:
        raise ServiceError("Only administrators can reopen complaints.")
    if complaint.status not in (S.STATUS_RESOLVED, S.STATUS_REJECTED):
        raise ServiceError("Only resolved or rejected complaints can be reopened.")
    if not (reason or "").strip():
        raise ServiceError("A reason is required to reopen a complaint.")
    _apply_status(complaint, S.STATUS_REVIEW, actor, f"Reopened: {reason.strip()}")
    complaint.resolved_at = None
    ns.notify_department(complaint.department_id, "Complaint reopened", complaint.reference_number, complaint.id)
    audit_service.log_action(actor, "complaint_reopened", "complaint", complaint.id, reason)
    db.session.commit()


# ---- Listing / filtering -----------------------------------------------------
def filter_complaints(query, args):
    """Apply GET-parameter filters to a Complaint query."""
    if args.get("status") in Complaint.STATUSES:
        query = query.filter(Complaint.status == args["status"])
    if args.get("category"):
        query = query.filter(Complaint.category == args["category"])
    if args.get("priority") in Complaint.PRIORITIES:
        query = query.filter(Complaint.priority == args["priority"])
    if args.get("department", type=int):
        query = query.filter(Complaint.department_id == args.get("department", type=int))
    if args.get("location"):
        query = query.filter(Complaint.address.ilike(f"%{args['location'].strip()}%"))
    if args.get("q"):
        like = f"%{args['q'].strip()}%"
        query = query.filter(or_(Complaint.title.ilike(like), Complaint.reference_number.ilike(like)))
    sort = args.get("sort", "newest")
    if sort == "oldest":
        query = query.order_by(Complaint.created_at.asc())
    elif sort == "priority":
        rank = case({"Critical": 0, "High": 1, "Medium": 2, "Low": 3}, value=Complaint.priority, else_=4)
        query = query.order_by(rank, Complaint.created_at.desc())
    else:
        query = query.order_by(Complaint.created_at.desc())
    return query
