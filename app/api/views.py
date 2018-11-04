import logging
import os
import pendulum # datetime with friendlier timezones
from flask_cors import CORS, cross_origin
from sqlalchemy import Date, Interval, desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, subqueryload
from sqlalchemy.sql import func, column, text
from sqlalchemy.sql.expression import cast
from . import api
from flask import request, jsonify
from .forms import newShelterForm
from ..models import db, Shelter, Call, Count

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
    today = pendulum.today(tz).subtract(days = int(daysback))
    print( today.isoformat(' '))
    count_calls = db.session.query(Count.shelter_id.label("shelterID"), Count.bedcount, Count.day, Count.call_id, Call.time)\
                  .join(Call).filter(Count.day == today.isoformat(' '))\
                  .subquery()

    counts = db.session.query(Shelter.name, Shelter.capacity, count_calls)\
             .outerjoin(count_calls, (Shelter.id == count_calls.c.shelterID))\
             .order_by(Shelter.name)

    result_dict = map(lambda q: q._asdict(), counts)
    ret = {"date": today.format('ddd, MMM D, YYYY'), "counts": list(result_dict)}
    return jsonify(ret)
    
@api.route('/callhistory/', methods=['GET'], defaults = {'page': 0})
@api.route('/callhistory/<page>/', methods=['GET'])
@cross_origin()
def callhistory(page):
    pagesize = 14 # days
    daysback = int(page) * pagesize + pagesize - 1

    today = pendulum.today(tz).subtract(days = (int(page) * pagesize))
    backthen = pendulum.today(tz).subtract(days=daysback)
    
    ''' TODO figure out how to do this in sqlalchemy's ORM '''
    q = text(
        """SELECT array_agg(counts.bedcount) as data, shelters.name as label 
         FROM generate_series(:start, :stop, interval '1 days') as day 
         CROSS JOIN  shelters 
         LEFT OUTER JOIN counts on counts.day = day.day AND counts.shelter_id = shelters.id 
         GROUP BY shelters.name
         ORDER BY shelters.name"""
    )
    shelter_dates = db.session.execute(q, {'start':backthen.to_date_string(), 'stop':today.to_date_string()} )
    results = {
        "dates": [d.to_date_string() for d in (today - backthen)],
        "shelters": [dict(row.items()) for row in shelter_dates]
    }
    return jsonify(results)
