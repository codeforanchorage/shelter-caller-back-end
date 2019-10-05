from . import pref_api, Prefs
import os
from sqlalchemy.orm import joinedload
from flask import request, jsonify, Response
from flask_jwt_simple import jwt_required, get_jwt_identity
from ..models import User

def isAdmin(user):
    db_user = User.query.options(joinedload('roles')).filter_by(username=user).first()
    return any(role.name == 'admin' for role in db_user.roles)

@pref_api.route('/', methods = ['GET'])
@jwt_required
def pref():
    '''
    Get preference object from DB
    Returns
        200:
            JSON prefs
    '''
    print(get_jwt_identity())
    if isAdmin(get_jwt_identity()):
        return jsonify(Prefs.toDict())
    return jsonify(msg="Permission denied"), 403
    
@pref_api.route('/set/', methods = ['POST'])
@jwt_required
def update_pref():
    '''
    set preference object from DB
    Returns
        200:
            JSON prefs
    '''
    if isAdmin(get_jwt_identity()):
        params = request.get_json()
        Prefs.update(params)
        return jsonify(Prefs.toDict())
    return  jsonify(msg="Permission denied"), 403