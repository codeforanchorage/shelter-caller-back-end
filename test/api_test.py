import pytest
from unittest.mock import Mock, patch
from app.models import Shelter
from app import db
from flask import g
from flask_jwt_simple import create_jwt
from app.api.decorators import add_user


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
