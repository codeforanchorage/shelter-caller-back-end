import pytest
from unittest.mock import Mock, patch
from app.models import Shelter
from app import db
from flask import g
from flask_jwt_simple import create_jwt
from app.api.decorators import add_user
from datetime import date, timedelta


@pytest.mark.current
@patch('flask_jwt_simple.get_jwt_identity')
def test_add_user_decorator(jwtMock, app_with_envion_DB):
    '''@add_user() should includes users roles from DB to g.'''
    jwtMock.return_value = 'admin'
    f = Mock()
    add_user()(f)()
    f.assert_called()
    assert any(r.name == 'admin' for r in g.user.roles)


@patch('flask_jwt_simple.get_jwt_identity')
def test_add_user_decorator_adds_user(jwtMock, app_with_envion_DB):
    '''@add_user() should add user from DB to g.'''
    jwtMock.return_value = 'admin'
    f = Mock()
    add_user()(f)()
    f.assert_called()
    assert g.user.username == 'admin'


def test_add_user_decorator_no_user(app_with_envion_DB):
    '''@add_user() should work with noo JWT user.'''
    f = Mock()
    add_user()(f)()
    f.assert_called()
    assert 'user' not in g


def test_get_shelters_auth(app_with_envion_DB):
    jwt = create_jwt(identity="admin")

    client = app_with_envion_DB.test_client()
    rv = client.get('/api/shelters/', environ_base={'HTTP_AUTHORIZATION': 'Bearer ' + jwt})
    assert rv.status_code == 200


def test_get_shelters_no_auth(app_with_envion_DB, test_shelters):
    '''/api/shelters should return 401 when auth is not present '''

    for s in test_shelters:
        db.session.add(Shelter(**s))

    db.session.commit()

    client = app_with_envion_DB.test_client()

    rv = client.get('/api/shelters/')
    assert rv.status_code == 401


def test_admin_login_good(app_with_envion_DB):
    '''should return a token and roles to authorized user'''
    client = app_with_envion_DB.test_client()
    rv = client.post(
        '/api/admin_login/',
        json={"user": "admin", "password": "password"}
    )
    json_response = rv.get_json()
    assert rv.status_code == 200
    assert 'jwt' in json_response
    assert json_response['roles'] == ['admin']


def test_admin_no_user(app_with_envion_DB):
    '''should return 400 when login is incomplete'''
    client = app_with_envion_DB.test_client()
    rv = client.post(
        '/api/admin_login/',
        json={"password": "password"}
    )
    assert rv.status_code == 400
    assert 'jwt' not in rv.get_json()


def test_admin_unauthorized(app_with_envion_DB):
    '''should return 401 for unknown logins'''
    client = app_with_envion_DB.test_client()
    rv = client.post(
        '/api/admin_login/',
        json={"user": "admin", "password": "bad_password"}
    )
    assert rv.status_code == 401
    assert 'jwt' not in rv.get_json()


def test_counts_today(app_with_envion_DB, counts):
    '''should provide counts for all shelters (even if they have no count)'''
    client = app_with_envion_DB.test_client()
    rv = client.get('/api/counts/')
    responses = rv.get_json()['counts']

    assert len(responses) == 2
    assert any(count['bedcount'] == 100 and count['id'] == 1 for count in responses)
    assert any(count['bedcount'] is None and count['id'] == 2 for count in responses)


def test_counts_previous(app_with_envion_DB, counts):
    '''should provide counts for all shelters (even if they have no count)'''
    client = app_with_envion_DB.test_client()
    rv = client.get('/api/counts/')
    responses = rv.get_json()['counts']

    assert len(responses) == 2
    assert any(count['bedcount'] == 100 and count['id'] == 1 for count in responses)
    assert any(count['bedcount'] is None and count['id'] == 2 for count in responses)


def test_counts_future_tomorrow(app_with_envion_DB, counts):
    '''should only provide a link to yesterday when getting today's counts'''
    client = app_with_envion_DB.test_client()
    rv = client.get('/api/counts/')
    responses = rv.get_json()
    yesterday = (date.today() - timedelta(days=1)).strftime('%Y%m%d')
    assert responses['tomorrow'] is None
    assert responses['yesterday'] == yesterday


def test_counts_yesterday(app_with_envion_DB, counts):
    '''should report counts for shelters from previous days'''
    client = app_with_envion_DB.test_client()
    yesterday = yesterday = (date.today() - timedelta(days=1)).strftime('%Y%m%d')
    rv = client.get(f'/api/counts/{yesterday}')
    responses = rv.get_json()['counts']

    assert len(responses) == 2
    assert any(count['bedcount'] == 31 and count['id'] == 1 for count in responses)
    assert any(count['bedcount'] == 32 and count['id'] == 2 for count in responses)


def test_counts_next_previous(app_with_envion_DB, counts):
    '''should not provide links to yesterday and tomorrow for past count queries'''
    client = app_with_envion_DB.test_client()
    yesterday = yesterday = (date.today() - timedelta(days=1)).strftime('%Y%m%d')
    rv = client.get(f'/api/counts/{yesterday}')
    responses = rv.get_json()
    today = date.today().strftime('%Y%m%d')
    daybefore = (date.today() - timedelta(days=2)).strftime('%Y%m%d')
    assert responses['tomorrow'] == today
    assert responses['yesterday'] == daybefore
