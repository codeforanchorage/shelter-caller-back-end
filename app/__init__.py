from flask import Flask, render_template, request, jsonify
from flask_jwt_simple import JWTManager
from config import config
from .models import db
from .prefs import Prefs

from flask import Blueprint

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    jwt = JWTManager(app)

    db.init_app(app)
    Prefs.init(app)

    print("Timezone:", prefs.Prefs['timezone'])
    from .prefs import pref_api as pref_api_blueprint
    app.register_blueprint(pref_api_blueprint, url_prefix="/prefs")

    '''/api will be for requests for data generated by the app used by the dashboard'''     
    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix="/api")

    '''/twilio is for requests from the twilio flow used primarily to enter or alter data in the db'''
    from .twilio_api import twilio_api as twilio_api_blueprint
    app.register_blueprint(twilio_api_blueprint, url_prefix="/twilio")

    
    return app
