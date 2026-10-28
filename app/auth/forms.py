from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Optional
from ..models import User
from ..utils.validators import validate_email_format, validate_phone, validate_password_strength


class RegisterForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(2, 120)])
    email = StringField("Email", validators=[DataRequired(), Length(max=255), validate_email_format])
    phone = StringField("Phone (optional)", validators=[Optional(), validate_phone])
    password = PasswordField("Password", validators=[DataRequired(), validate_password_strength])
    confirm = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password", "Passwords must match.")])

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("An account with this email already exists.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), validate_email_format])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Keep me signed in")


class ProfileForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(2, 120)])
    phone = StringField("Phone", validators=[Optional(), validate_phone])
    current_password = PasswordField("Current password (only to change password)", validators=[Optional()])
    new_password = PasswordField("New password", validators=[Optional(), validate_password_strength])
