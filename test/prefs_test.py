import os
import pytest
from app import create_app, db, create_prefs, register_blueprints
from app.prefs import Prefs
from app.models import Pref
from testing.postgresql import Postgresql


environ = {
    "APP_NAME": "test_app",
    "PEND_TZ": "America/Test_zone",
    "OPEN": "02:00",
    "CLOSED": "12:00",
    "DAY_CUTOFF": "02:00"
}
db_environ = {
    "app_id":  environ["APP_NAME"],    
    "timezone": "America/DB_Test_zone",
    "enforce_hours": False, 
    "open_time": "12:00",
    "close_time": "18:00",
    "start_day": "12:00" 
}

@pytest.fixture
def client():
    _app = create_app('testing')
    db.create_all(app = _app)
    with _app.app_context():
        yield _app
    register_blueprints(_app)
    db.drop_all(app = _app)

@pytest.fixture
def prefs_from_envion(monkeypatch, client):
    for k, v in environ.items():
        monkeypatch.setenv(k,v)
    return create_prefs(client)
   
@pytest.fixture
def prefs_from_DB(monkeypatch, client):
    for k, v in environ.items():
        monkeypatch.setenv(k,v)
    p = Pref(**db_environ)
    db.session.add(p)
    db.session.commit()
    return create_prefs(client)

@pytest.fixture
def app_with_prefs(prefs_from_envion)

def test_prefs_environ(prefs_from_envion):
    '''Preferences should default to env variables'''   
    assert Prefs['timezone'] == environ['PEND_TZ']

def test_prefs_set(prefs_from_envion):
    '''Setting item should set Pref item '''
    Prefs['timezone'] = "testVal2"
    assert Prefs['timezone'] == 'testVal2'

def test_prefs_set_DB(prefs_from_envion):
    '''Setting item on Prefs instacne should set DB value '''
    Prefs['timezone'] = "testVal2"
    Prefs['start_day'] = "10:00"
    p = Pref.query.get(environ['APP_NAME'])
    assert p.timezone == 'testVal2'
    assert p.start_day == '10:00'

def test_enforce_hours_default(prefs_from_envion):
    '''Enforce Hourse should default to True'''
    assert Prefs['enforce_hours'] == True

def test_prefs_default_DB(prefs_from_DB):
    '''Preferences should use DB values when available'''
    assert Prefs['timezone'] == db_environ['timezone']
    assert Prefs['start_day'] == db_environ['start_day']

def test_get_defaults(prefs_from_envion):
    with app.test_request_context('/api/prefs/'):
        print("done")
    return True