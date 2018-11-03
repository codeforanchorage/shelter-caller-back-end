import logging
import os
import pendulum # datetime with friendlier timezones
from flask_cors import CORS, cross_origin
from sqlalchemy import Date, Interval, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, subqueryload
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import cast
from . import api
from flask import request, jsonify
from .forms import newShelterForm
from ..models import db, Shelter, Call

tz = os.environ['PEND_TZ'] 

##################
#### SHELTERS ####
##################
@api.route('/shelters/', methods = ['GET', 'POST'])
@cross_origin()
def get_shelters():
    shelters = Shelter.query.order_by('name').all()
    return jsonify([s.toDict() for s in shelters])

@api.route('/add_shelters/', methods = ['GET', 'POST'])
@cross_origin()
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
@cross_origin()
def delete_shelter(shelter_id):
    Shelter.query.filter_by(id=shelter_id).delete()
    db.session.commit()
    return jsonify({"result":"success"})

@api.route('/update_shelter/', methods=['POST'])
@cross_origin()
def update_shelter():
    form = newShelterForm()
    shelter = {}
    shelter['id']       = form.id.data
    shelter['name']     = form.name.data
    shelter['phone']    = form.phone.data
    shelter['login_id'] = form.login_id.data
    shelter['capacity'] = form.capacity.data
    shelter['active']   = form.active.data
    shelter = Shelter(**shelter)
    #form = newShelterForm()
    
    #shelter = Shelter.query.get_or_404(form.id.data)
    #form.populate_obj(shelter)
    
    try:
        shelter = db.session.merge(shelter)
        db.session.commit()
    except exc.IntegrityError as e:
        logging.warning(e.orig.args)
        db.session().rollback()
        return jsonify({"error": 'Values must be unique'})
    return jsonify({"result": shelter.toDict()})
   
##################
####  Calls   ####
##################

@api.route('/calls/', methods=['GET'], defaults = {'daysback': 0})
@api.route('/calls/<daysback>', methods=['GET'])
@cross_origin()
def calls(daysback):
    # start of today utc
    today = pendulum.today(tz).subtract(days = int(daysback))
    print(today)
    calls = db.session.query(Call.shelter_id, func.jsonb_build_object('count', Call.bedcount, 'time', Call.time, 'id', Call.id).label('calls'))\
            .filter(cast(func.timezone(tz, Call.time), Date) == cast(today, Date))\
            .order_by(Call.time)\
            .subquery()
    # becuase of the outer join the calls array may be [null]
    # arr_remove will remove it from the array and produce the much nicer mepty array: []
    shelters = db.session.query(Shelter.name, Shelter.capacity, func.array_remove(func.array_agg(calls.c.calls), None).label('calls'))\
               .outerjoin(calls, Shelter.id == calls.c.shelter_id)\
               .group_by(Shelter.name, Shelter.capacity)\
               .order_by(Shelter.name).all()
    
    result_dict = map(lambda q: q._asdict(), shelters)
    ret = {"date": today.format('ddd, MMM D, YYYY'), "counts": list(result_dict)}
    return jsonify(ret)

@api.route('/callhistory/', methods=['GET'], defaults = {'page': 0})
@api.route('/callhistory/<page>/', methods=['GET'])
@cross_origin()
def callhistory(page):
    pagesize = 14 # days
    daysback = int(page) * pagesize + pagesize - 1
    print(daysback, page)
    today = pendulum.today(tz).subtract(days = (int(page) * pagesize))
    backthen = pendulum.today(tz).subtract(days=daysback)

    dateRange = {d.to_date_string():[] for d in (today - backthen)}
    calls = db.session.query(Shelter.name , cast(func.timezone(tz, Call.time), Date).label('day'), func.array_agg(func.jsonb_build_object('count', Call.bedcount, 'time', Call.time)).label('calls'))\
            .filter((Call.time > backthen) & (Call.time <= today.add(days = 1)))\
            .outerjoin(Call, Shelter.id == Call.shelter_id)\
            .group_by('day', Shelter.name)\
            .order_by('day')
    
    for row in calls:
        row = row._asdict()
        row['day'] = str(row['day']) # prevent jsonify from convertint datetime.date to GMT string.
        row['lastcall'] = max(row['calls'], key=lambda item: item['time'])
        dateRange[str(row['day'])].append(row)
    
    return jsonify(dateRange)
