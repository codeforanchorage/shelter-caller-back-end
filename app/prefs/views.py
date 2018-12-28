from . import pref_api, Prefs
import os
from flask import request, jsonify, Response
from flask_jwt_simple import jwt_required, get_jwt_identity


@pref_api.route('/', methods = ['GET'])
@jwt_required
def pref():
    if get_jwt_identity() != os.environ['ADMIN_USER']:
        return jsonify(msg="Permission denied"), 403
    return jsonify(Prefs.toDict())

@pref_api.route('/set/', methods = ['POST'])
@jwt_required
def update_pref():
    if get_jwt_identity() != os.environ['ADMIN_USER']:
        return jsonify(msg="Permission denied"), 403
    params = request.get_json()
    Prefs.update(params)
    return jsonify(Prefs.toDict())