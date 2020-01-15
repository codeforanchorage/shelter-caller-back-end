from unittest.mock import patch
from app.prefs import Prefs
from app.models import Pref
from . import environ, db_environ
from flask_jwt_simple import create_jwt


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


@patch('app.prefs.views.isAdmin')
def test_get_defaults_good_jwt(isAdmin_mock, app_with_envion):
    ''' Returns correct preference values '''
    isAdmin_mock.return_value = True

    jwt = create_jwt(identity=environ['ADMIN_USER'])
    client = app_with_envion.test_client()
    rv = client.get('/api/prefs/',
                    environ_base={'HTTP_AUTHORIZATION': 'Bearer ' + jwt})
    assert rv.status_code == 200
    res_data = rv.json
    assert res_data['close_time'] == environ['CLOSED']
    assert res_data['enforce_hours'] == True
    assert res_data['open_time'] == environ['OPEN']
    assert res_data['timezone'] == environ['PEND_TZ']
