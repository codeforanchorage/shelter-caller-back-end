import pytest
from app import create_app, db, create_prefs, register_blueprints
from app.models import Pref


environ = {
    "APP_NAME": "test_app",
    "PEND_TZ": "America/Anchorage",
    "OPEN": "02:00",
    "CLOSED": "12:00",
    "DAY_CUTOFF": "02:00",
    "ADMIN_USER": "test_admin",
    "ADMIN_PW": "test_admin_pw",
    "TWILIO_FLOW_BASE_URL": 'https://twilio_test.com/v1/Flows/',
    "TWILIO_FLOW_ID": 'testID'
}

db_environ = {
    "app_id":  environ["APP_NAME"],    
    "timezone": "America/Anchorage",
    "enforce_hours": False, 
    "open_time": "12:00",
    "close_time": "18:00",
    "start_day": "12:00" 
}
@pytest.fixture
def client():
    _app = create_app('testing')
    db.create_all(app = _app)
    register_blueprints(_app)
    with _app.app_context():
        yield _app  
    db.drop_all(app = _app)

@pytest.fixture
def app_with_envion(monkeypatch, client):
    for k, v in environ.items():
        monkeypatch.setenv(k,v)
    create_prefs(client)
    return client

@pytest.fixture
def app_with_envion_DB(monkeypatch, client):
    for k, v in environ.items():
        monkeypatch.setenv(k,v)
    p = Pref(**db_environ)
    db.session.add(p)
    db.session.commit()
    create_prefs(client)
    return client
