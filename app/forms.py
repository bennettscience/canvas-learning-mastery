from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, SubmitField, HiddenField
from wtforms.validators import DataRequired
from app.models import Outcome


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember me')
    submit = SubmitField('Sign In')


class StoreOutcomesForm(FlaskForm):
    id = HiddenField('course_id')
    assignment_groups = SelectField('Assignment Group', coerce=int, choices=[])
    submit = SubmitField('Import Assignments')


class SelectSectionForm(FlaskForm):
    id = HiddenField('course_id')
    sections = SelectField('Course Section', coerce=int, choices=[])
