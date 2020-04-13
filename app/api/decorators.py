from functools import wraps
import flask_jwt_simple as jwt
from sqlalchemy.orm import joinedload
from ..models import User
from flask import jsonify, g


def role_required(allowed_roles):
    '''
    Helper decorator for routes to check that a user is
    in the passed in list of allowed_roles.

    Decorator must go after @jwt_required to we have the token available

    Args:
        allowed_roles: a list of allowed user roles

    Returns:
        Decorator
    '''
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = jwt.get_jwt_identity()

            db_user = User.query.options(joinedload('roles')).filter_by(username=user).first()
            # make user object available to routes on flask.g
            g.user = db_user
            for role in db_user.roles:
                if role.name in allowed_roles:
                    return f(*args, **kwargs)
            return jsonify(msg="Permission denied"), 403
        return decorated_function
    return decorator


def add_user():
    ''' Decorator for routes to add user with roles to route'''
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = jwt.get_jwt_identity()
            if user:
                db_user = User.query.options(joinedload('roles')).filter_by(username=user).first()
                # make user object available to routes on flask.g
                g.user = db_user
            return f(*args, **kwargs)
        return decorated_function
    return decorator
