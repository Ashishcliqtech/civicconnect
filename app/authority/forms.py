from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import SelectField, TextAreaField
from wtforms.validators import DataRequired, Length


class StatusForm(FlaskForm):
    status = SelectField("New status", validators=[DataRequired()])
    message = TextAreaField("Message to citizen (optional)", validators=[Length(max=1000)])


class RejectForm(FlaskForm):
    reason = TextAreaField("Reason for rejection", validators=[DataRequired(), Length(5, 1000)])


class NoteForm(FlaskForm):
    message = TextAreaField("Internal note (citizens cannot see this)", validators=[DataRequired(), Length(2, 1000)])


class InfoRequestForm(FlaskForm):
    message = TextAreaField("What information do you need?", validators=[DataRequired(), Length(5, 1000)])


class ResolutionForm(FlaskForm):
    action_taken = TextAreaField("Action taken", validators=[DataRequired(), Length(10, 2000)])
    proof = FileField("Resolution proof photo", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Images only.")])
