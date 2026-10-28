import re
from wtforms.validators import ValidationError

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\+?[0-9 \-]{7,15}$")


def validate_email_format(form, field):
    if not EMAIL_RE.match((field.data or "").strip()):
        raise ValidationError("Enter a valid email address.")


def validate_phone(form, field):
    if field.data and not PHONE_RE.match(field.data.strip()):
        raise ValidationError("Enter a valid phone number (7-15 digits).")


def validate_password_strength(form, field):
    pw = field.data or ""
    if len(pw) < 8 or not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        raise ValidationError("Password must be 8+ characters with letters and numbers.")


def validate_latitude(form, field):
    if field.data is None or not -90 <= field.data <= 90:
        raise ValidationError("Latitude must be between -90 and 90.")


def validate_longitude(form, field):
    if field.data is None or not -180 <= field.data <= 180:
        raise ValidationError("Longitude must be between -180 and 180.")
