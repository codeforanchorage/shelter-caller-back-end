import os
import pytest
from app import create_app, db, create_prefs, register_blueprints
from app.prefs import Prefs
from app.models import Pref
from testing.postgresql import Postgresql

from flask_jwt_simple import create_jwt

environ = {
    "APP_NAME": "test_app",
    "PEND_TZ": "America/Test_zone",
    "OPEN": "02:00",
    "CLOSED": "12:00",
    "DAY_CUTOFF": "02:00",
    "ADMIN_USER": "test_admin",
    "ADMIN_PW": "test_admin_pw"

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

#@pytest.fixture
#def app_with_prefs(prefs_from_envion)

def test_prefs_environ(app_with_envion):
    '''Preferences should default to env variables'''   
    assert Prefs['timezone'] == environ['PEND_TZ']

def test_prefs_set(app_with_envion):
    '''Setting item should set Pref item '''
    Prefs['timezone'] = "testVal2"
    assert Prefs['timezone'] == 'testVal2'

def test_prefs_set_DB(app_with_envion):
    '''Setting item on Prefs instacne should set DB value '''
    Prefs['timezone'] = "testVal2"
    Prefs['start_day'] = "10:00"
    p = Pref.query.get(environ['APP_NAME'])
    assert p.timezone == 'testVal2'
    assert p.start_day == '10:00'

def test_enforce_hours_default(app_with_envion):
    '''Enforce Hourse should default to True'''
    assert Prefs['enforce_hours'] == True

def test_prefs_default_DB(app_with_envion_DB):
    '''Preferences should use DB values when available'''
    assert Prefs['timezone'] == db_environ['timezone']
    assert Prefs['start_day'] == db_environ['start_day']

def test_get_defaults(app_with_envion):
    ''' Returns 401 Unauthorized without JWT '''
    client = app_with_envion.test_client()
    rv = client.get('/api/prefs/')
    assert rv.status_code == 401

def test_get_defaults_bad_jwt(app_with_envion):
    ''' Returns 403 with incorrect identity '''
    jwt = create_jwt(identity="Hacker")

    client = app_with_envion.test_client()
    rv = client.get('/api/prefs/',
                     environ_base={'HTTP_AUTHORIZATION': 'Bearer ' + jwt})
    assert rv.status_code == 403


def test_get_defaults_good_jwt(app_with_envion):
    ''' Returns 200 with correct token '''
    jwt = create_jwt(identity=environ['ADMIN_USER'])
    client = app_with_envion.test_client()
    rv = client.get('/api/prefs/',
                     environ_base={'HTTP_AUTHORIZATION': 'Bearer ' + jwt})
    assert rv.status_code == 200

def test_get_defaults_good_jwt(app_with_envion):
    ''' Returns correct preference values '''
    jwt = create_jwt(identity=environ['ADMIN_USER'])
    client = app_with_envion.test_client()
    rv = client.get('/api/prefs/',
                     environ_base={'HTTP_AUTHORIZATION': 'Bearer ' + jwt})
    res_data = rv.json
    assert res_data['close_time'] == environ['CLOSED']
    assert res_data['enforce_hours'] == True
    assert res_data['open_time'] == environ['OPEN']
    assert res_data['timezone'] == environ['PEND_TZ']

