from flask import Flask, render_template, request, jsonify
from flask_jwt_simple import JWTManager
from config import config
from .models import db

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    jwt = JWTManager(app)

    db.init_app(app)
    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix="/api")

    from .twilio_api import twilio_api as twilio_api_blueprint
    app.register_blueprint(twilio_api_blueprint, url_prefix="/twilio")

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
