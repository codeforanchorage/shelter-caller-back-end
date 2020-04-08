from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, BooleanField
from wtforms.validators import DataRequired


class newShelterForm(FlaskForm):
    name = StringField('name', validators=[DataRequired()])
    login_id = IntegerField('login_id', validators=[DataRequired()])
    description = StringField('description')
    phone = StringField('phone', validators=[DataRequired()])
    capacity = IntegerField('capacity', validators=[DataRequired()])
    id = IntegerField('id')
    submit = SubmitField("Add")
    active = BooleanField("active", validators=[DataRequired()])
    visible = BooleanField("visible")
    public = BooleanField("public")
