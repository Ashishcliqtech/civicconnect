from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from ..models import User, Department, Category
from ..utils.validators import validate_email_format, validate_password_strength, validate_phone


class UserForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(2, 120)])
    email = StringField("Email", validators=[DataRequired(), validate_email_format])
    phone = StringField("Phone", validators=[Optional(), validate_phone])
    role = SelectField("Role", choices=[(r, r.title()) for r in User.ROLES])
    department_id = SelectField("Department (officers)", coerce=int)
    password = PasswordField("Password", validators=[Optional(), validate_password_strength])
    is_active = BooleanField("Active", default=True)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.department_id.choices = [(0, "— none —")] + [(d.id, d.name) for d in Department.query.order_by(Department.name)]

    def validate_email(self, field):
        existing = User.query.filter_by(email=field.data.strip().lower()).first()
        if existing and (self.user is None or existing.id != self.user.id):
            raise ValidationError("Email already in use.")


class DepartmentForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(2, 120)])
    description = TextAreaField("Description", validators=[Length(max=500)])
    contact_email = StringField("Contact email", validators=[Optional(), validate_email_format])
    is_active = BooleanField("Active", default=True)


class CategoryForm(FlaskForm):
    name = StringField("Category name", validators=[DataRequired(), Length(2, 80)])
    icon = StringField("Lucide icon name", validators=[Length(max=40)], default="alert-circle")

    def validate_name(self, field):
        if Category.query.filter_by(name=field.data.strip()).first():
            raise ValidationError("Category already exists.")


class AssignForm(FlaskForm):
    department_id = SelectField("Department", coerce=int)
    officer_id = SelectField("Officer (optional)", coerce=int)
    priority = SelectField("Priority", choices=[(p, p) for p in ("Low", "Medium", "High", "Critical")])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.department_id.choices = [(d.id, d.name) for d in Department.query.filter_by(is_active=True).order_by(Department.name)]
        self.officer_id.choices = [(0, "— any officer in department —")] + [
            (u.id, f"{u.full_name} ({u.department.name if u.department else 'no dept'})")
            for u in User.query.filter_by(role=User.ROLE_AUTHORITY, is_active=True).order_by(User.full_name)]


class ReopenForm(FlaskForm):
    reason = TextAreaField("Reason", validators=[DataRequired(), Length(5, 1000)])
