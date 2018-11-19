import logging
import os
import pendulum # datetime with friendlier timezones
from flask_cors import CORS, cross_origin
from sqlalchemy import Date, Interval, desc, select, String, distinct
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, subqueryload
from sqlalchemy.sql import func, column, text
from sqlalchemy.sql.expression import cast, true
from . import api
from flask import request, jsonify
from .forms import newShelterForm
from ..models import db, Shelter, Count, Log

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
@cross_origin()
def counts(daysback):
    ''' Results the lastest counts per shelter '''
    today = pendulum.today(tz).subtract(days = int(daysback))
    print( today.isoformat(' '))

    count_calls = db.session.query(Count.shelter_id.label("call_shelterID"), Count.bedcount, Count.day, Count.time)\
                  .filter(Count.day == today.isoformat(' '))\
                  .subquery()

    counts = db.session.query(Shelter.name, Shelter.capacity, Shelter.id, count_calls)\
             .outerjoin(count_calls, (Shelter.id == count_calls.c.call_shelterID))\
             .order_by(Shelter.name)

    result_dict = map(lambda q: q._asdict(), counts)
    ret = {"date": today.format('ddd, MMM D, YYYY'), "counts": list(result_dict)}
    return jsonify(ret)
    
@api.route('/counthistory/', methods=['GET'], defaults = {'page': 0})
@api.route('/counthistory/<page>/', methods=['GET'])
@cross_origin()
def counthistory(page):
    ''' Final count history for all shelters. Used for chart showing counts over time '''
    pagesize = 14 # days
    daysback = int(page) * pagesize + pagesize - 1

    today = pendulum.today(tz).subtract(days = (int(page) * pagesize))
    backthen = pendulum.today(tz).subtract(days=daysback)
    
    date_list = func.generate_series(backthen, today, '1 day').alias('gen_day')
    time_series = db.session.query(Shelter.name.label('label'), func.array_agg(Count.bedcount).label('data'))\
                  .join(date_list, true())\
                  .outerjoin(Count, (Count.day == cast(column('gen_day'), Date)) &\
                                    (Count.shelter_id == Shelter.id))\
                  .group_by(Shelter.name)\
                  .order_by(Shelter.name)

    results = {
        "dates": [d.to_date_string() for d in (today - backthen)],
        "shelters": [row._asdict() for row in time_series]
    }
    return jsonify(results)


@api.route('/logs/<shelterid>/', methods=['GET'])
@api.route('/logs/<shelterid>/<page>/', methods=['GET'])
@cross_origin()
def logs(shelterid, page=0):
    '''Provives a list of logs for a particular shelter'''
    pagesize = 15 #records
    offset = pagesize * int(page)
    shelter = Shelter.query.get_or_404(shelterid)
    total_calls = db.session.query(func.count(Log.id)).filter_by(shelter_id=shelterid).scalar()
    print(total_calls)
    logs = db.session.query(Log)\
            .filter_by(shelter_id = shelterid)\
            .order_by(Log.time.desc())\
            .limit(pagesize).offset(offset)

    result = [row.toDict() for row in logs]

    return jsonify(shelter=shelter.name, logs=result, total_calls=total_calls, page_size=pagesize)