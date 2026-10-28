from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, FloatField, IntegerField
from wtforms.validators import DataRequired, Length, NumberRange, InputRequired
from ..models import Category
from ..utils.validators import validate_latitude, validate_longitude


class ComplaintForm(FlaskForm):
    title = StringField("Complaint title", validators=[DataRequired(), Length(5, 150)])
    category = SelectField("Category", validators=[DataRequired()])
    description = TextAreaField("Detailed description", validators=[DataRequired(), Length(20, 2000)])
    address = StringField("Address or landmark", validators=[DataRequired(), Length(5, 255)])
    latitude = FloatField("Latitude", validators=[InputRequired(), validate_latitude])
    longitude = FloatField("Longitude", validators=[InputRequired(), validate_longitude])
    photo = FileField("Photo (optional)", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Images only.")])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category.choices = [(c.name, c.name) for c in Category.query.filter_by(is_active=True).order_by(Category.name)]


class FeedbackForm(FlaskForm):
    rating = IntegerField("Rating (1-5)", validators=[InputRequired(), NumberRange(1, 5)])
    comments = TextAreaField("Comments (optional)", validators=[Length(max=1000)])


class CommentForm(FlaskForm):
    message = TextAreaField("Message", validators=[DataRequired(), Length(2, 1000)])
