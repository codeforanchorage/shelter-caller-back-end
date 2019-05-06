import logging
import os
from functools import wraps
import pendulum # datetime with friendlier timezones
from flask_cors import CORS, cross_origin
from sqlalchemy import Date, Interval, desc, select, String, distinct
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, subqueryload
from sqlalchemy.sql import func, column, text
from sqlalchemy.sql.expression import cast, true
from . import api

from flask import request, jsonify, g
from flask_jwt_simple import (
    jwt_required, create_jwt, get_jwt_identity
)
from .forms import newShelterForm
from ..models import db, Shelter, Count, Log, User, Role
from ..prefs import Prefs
#tz = Prefs['timezone']

##############
#### AUTH ####
##############
def role_required(allowed_roles):
    ''' Helper decorator for routes to check that a user is in the passed in list of allowed_roles'''
    # Make sure the decorator goes after @jwt_required to we have the token available
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_jwt_identity()
            db_user = User.query.filter_by(username=user).first()
            # make user object available to routes on flask.g
            g.user = db_user
            for role in db_user.roles:
                if role.name in allowed_roles:
                    return f(*args, **kwargs)
            return jsonify(msg="Permission denied"), 403
        return decorated_function
    return decorator

@api.route('/admin_login/', methods = ['POST'])
def login():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400

    params = request.get_json()
    user = params.get('user', None)
    password = params.get('password', None)
    if not user:
        return jsonify({"msg": "Missing username parameter"}), 400
    if not password:
        return jsonify({"msg": "Missing password parameter"}), 400
 
    db_user = User.query.filter_by(username=user).first()
    if not db_user or db_user.password != password:
        return jsonify({"msg": "Bad username or password"}), 401
    roles = [role.name for role in db_user.roles]
    #ret = {'jwt': create_jwt(identity=user)}
    return jsonify(jwt=create_jwt(identity=user), roles=roles), 200

##################
#### SHELTERS ####
##################
@api.route('/shelters/', methods = ['GET', 'POST'])
@jwt_required
@role_required(['admin'])
def get_shelters():
    #if get_jwt_identity() != os.environ['ADMIN_USER']:
    #    return jsonify(msg="Permission denied"), 403

    shelters = Shelter.query.order_by('name').all()
    return jsonify([s.toDict() for s in shelters])

@api.route('/add_shelters/', methods = ['GET', 'POST'])
@jwt_required
def add_shelter():
    form = newShelterForm()
    if form.validate_on_submit():
        shelter = {}
        shelter['name']     = form.name.data
        shelter['phone']    = form.phone.data
        shelter['login_id'] = form.login_id.data
        shelter['capacity'] = form.capacity.data
        shelter['active']   = form.active.data
        shelter = Shelter(**shelter)
        try:
            db.session.add(shelter)
            db.session.commit()
        except IntegrityError as e:
            logging.warning(e.orig.args)
            db.session().rollback()
            return jsonify({error: "Values must be unique"})
    return jsonify({result: shelter.toDict()})

@api.route('/delete_shelter/<shelter_id>', methods = ['GET'])
@jwt_required
@role_required(['admin'])
def delete_shelter(shelter_id):
    Shelter.query.filter_by(id=shelter_id).delete()
    db.session.commit()
    return jsonify({"result":"success"})

@api.route('/update_shelter/', methods=['POST'])
@jwt_required
@role_required(['admin'])
def update_shelter():
    form = newShelterForm()
    shelter = {}
    shelter['id']       = form.id.data
    shelter['name']     = form.name.data
    shelter['phone']    = form.phone.data
    shelter['login_id'] = form.login_id.data
    shelter['capacity'] = form.capacity.data
    shelter['active']   = form.active.data
    shelter['visible']  = form.visible.data
   
    shelter = Shelter(**shelter)
    
    try:
        shelter = db.session.merge(shelter)
        db.session.commit()
    except exc.IntegrityError as e:
        logging.warning(e.orig.args)
        db.session().rollback()
        return jsonify({"error": 'Values must be unique'})
    return jsonify({"result": shelter.toDict()})
   
##################
####  Counts  ####
##################

@api.route('/counts/', methods=['GET'], defaults = {'daysback': 0})
@api.route('/counts/<daysback>', methods=['GET'])
@jwt_required
@role_required(['admin', 'visitor'])
def counts(daysback):
    ''' Results the lastest counts per shelter '''
    tz = Prefs['timezone']
    today = pendulum.today(tz).subtract(days = int(daysback))

    # only show person count to admin
    if 'admin' in [role.name for role in g.user.roles]:
        count_calls = db.session.query(Count.shelter_id.label("call_shelterID"), Count.bedcount,  Count.personcount, Count.day, Count.time)\
                    .filter(Count.day == today.isoformat(' '))\
                    .subquery()
    else:
        count_calls = db.session.query(Count.shelter_id.label("call_shelterID"), Count.bedcount, Count.day, Count.time)\
                  .filter(Count.day == today.isoformat(' '))\
                  .subquery()

    counts = db.session.query(Shelter.name, Shelter.capacity, Shelter.id, count_calls)\
             .outerjoin(count_calls, (Shelter.id == count_calls.c.call_shelterID))\
             .filter(Shelter.visible == True)\
             .order_by(Shelter.name)

    result_dict = map(lambda q: q._asdict(), counts)
    ret = {"date": today.format('ddd, MMM D, YYYY'), "counts": list(result_dict)}
    return jsonify(ret)
    
@api.route('/counthistory/', methods=['GET'], defaults = {'page': 0})
@api.route('/counthistory/<page>/', methods=['GET'])
@jwt_required
@role_required(['admin', 'visitor'])
def counthistory(page):
    ''' Final count history for all shelters. Used for chart showing counts over time '''
    tz = Prefs['timezone']

    pagesize = 14 # days
    daysback = int(page) * pagesize + pagesize - 1

    today = pendulum.today(tz).subtract(days = (int(page) * pagesize))
    backthen = pendulum.today(tz).subtract(days=daysback)
    
    date_list = func.generate_series(cast(backthen.to_date_string(), Date), cast(today.to_date_string(), Date), '1 day').alias('gen_day')

    time_series = db.session.query(Shelter.name.label('label'), func.array_agg(Count.bedcount).label('data'))\
                  .join(date_list, true())\
                  .outerjoin(Count, (Count.day == column('gen_day')) &\
                                    (Count.shelter_id == Shelter.id))\
                  .filter(Shelter.visible == True)\
                  .group_by(Shelter.name)\
                  .order_by(Shelter.name)

    results = {
        "dates": [d.to_date_string() for d in (today - backthen)],
        "shelters": [row._asdict() for row in time_series]
    }
    return jsonify(results)


@api.route('/logs/<shelterid>/', methods=['GET'])
@api.route('/logs/<shelterid>/<page>/', methods=['GET'])
@jwt_required
@role_required(['admin'])
def logs(shelterid, page=0):
    '''Provives a list of logs for a particular shelter'''
    pagesize = 15 #records
    offset = pagesize * int(page)
    shelter = Shelter.query.get_or_404(shelterid)
    total_calls = db.session.query(func.count(Log.id)).filter_by(shelter_id=shelterid).scalar()
    logs = db.session.query(Log)\
            .filter_by(shelter_id = shelterid)\
            .order_by(Log.time.desc())\
            .limit(pagesize).offset(offset)

    result = [row.toDict() for row in logs]

    return jsonify(shelter=shelter.name, logs=result, total_calls=total_calls, page_size=pagesize)