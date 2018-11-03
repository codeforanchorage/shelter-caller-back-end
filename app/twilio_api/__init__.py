from flask import Blueprint

twilio_api = Blueprint('twilio_api', __name__)

from . import views
