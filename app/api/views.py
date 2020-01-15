import logging
from functools import wraps
import pendulum
from pendulum.exceptions import ParserError
from sqlalchemy import Date
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func, column
from sqlalchemy.sql.expression import cast, true
from . import api

from flask import request, jsonify, g
from flask_jwt_simple import (
    jwt_required, create_jwt, get_jwt_identity
)
from .forms import newShelterForm
from ..models import db, Shelter, Count, Log, User
from ..prefs import Prefs


##############
#    AUTH    #
##############
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
            user = get_jwt_identity()
            db_user = User.query.options(joinedload('roles')).filter_by(username=user).first()
            # make user object available to routes on flask.g
            g.user = db_user
            for role in db_user.roles:
                if role.name in allowed_roles:
                    return f(*args, **kwargs)
            return jsonify(msg="Permission denied"), 403
        return decorated_function
    return decorator


@api.route('/admin_login/', methods=['POST'])
def login():
    '''
    User Login
    parameters:
        user, password
    response:
        200:
            jwt: token
            roles: list of roles user is authorized for
        400:
            missing credentials
        401:
            not authorized
    '''
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
    return jsonify(jwt=create_jwt(identity=user), roles=roles), 200

##################
#    SHELTERS    #
##################
@api.route('/shelters/', methods=['GET', 'POST'])
@jwt_required
@role_required(['admin'])
def get_shelters():
    '''
    All the current shelters
    Response:
        200:
            JSON array containing an object for each shelter
    '''
    shelters = Shelter.query.order_by('name').all()
    return jsonify([s.toDict() for s in shelters])


@api.route('/delete_shelter/<shelter_id>', methods=['GET'])
@jwt_required
@role_required(['admin'])
def delete_shelter(shelter_id):
    '''
    Deletes a shelter
    Response:
        200:
            JSON object with result: success
    '''
    Shelter.query.filter_by(id=shelter_id).delete()
    db.session.commit()
    return jsonify({"result": "success"})


@api.route('/update_shelter/', methods=['POST'])
@jwt_required
@role_required(['admin'])
def update_shelter():
    '''
    Updates or creates an new shelter
    Response:
        200:
            JSON object with the shelter data
    '''
    form = newShelterForm()
    shelter = {}
    shelter['id'] = form.id.data
    shelter['name'] = form.name.data
    shelter['description'] = form.description.data
    shelter['phone'] = form.phone.data or None
    shelter['login_id'] = form.login_id.data
    shelter['capacity'] = form.capacity.data
    shelter['active'] = form.active.data
    shelter['visible'] = form.visible.data

    shelter = Shelter(**shelter)

    try:
        shelter = db.session.merge(shelter)
        db.session.commit()
    except IntegrityError as e:
        logging.warning(e.orig.args)
        db.session().rollback()
        return jsonify({"error": 'Values must be unique'}), 400
    return jsonify({"result": shelter.toDict()})


##################
#     Counts     #
##################
@api.route('/counts/<datestring>', methods=['GET'])
@jwt_required
@role_required(['admin', 'visitor', 'public'])
def counts(datestring):
    '''
    Returns the lastest counts per shelter for a given date-string
    The date will be interpreted in the timezone set in the prefs
    Returns:
        200:
            JSON object with:
                yesterday (YYMMDD)
                tomorrow (YYMMDD)
                counts: list of shelters and this day's counts
    '''
    tz = Prefs['timezone']
    now = pendulum.today(tz)

    try:
        today = pendulum.parse(datestring, tz=tz)
    except ParserError:
        today = now

    # help browsers navigate dates without worring about local timezone
    yesterday = today.subtract(days=1).format('YYYYMMDD')
    if today < now:
        tomorrow = today.add(days=1).format('YYYYMMDD')
    else:
        tomorrow = None

    # only show person count to admin
    if 'admin' in [role.name for role in g.user.roles]:
        count_calls = db.session.query(
            Count.shelter_id.label("call_shelterID"),
            Count.bedcount,
            Count.personcount,
            Count.day,
            Count.time)\
            .filter(Count.day == today.isoformat(' '))\
            .subquery()
    else:
        count_calls = db.session.query(Count.shelter_id.label("call_shelterID"), Count.bedcount, Count.day, Count.time)\
            .filter(Count.day == today.isoformat(' '))\
            .subquery()

    # Only admins and visitors see percentages
    if set(['admin', 'visitor']).isdisjoint(set([role.name for role in g.user.roles])):
        shelterQuery = db.session.query(Shelter.name, Shelter.description, Shelter.id, count_calls)
    else:
        shelterQuery = db.session.query(Shelter.name, Shelter.description, Shelter.capacity, Shelter.id, count_calls)

    counts = shelterQuery\
        .outerjoin(count_calls, (Shelter.id == count_calls.c.call_shelterID))\
        .filter(Shelter.visible == True)\
        .order_by(Shelter.name)

    result_dict = map(lambda q: q._asdict(), counts)
    ret = {
        "yesterday": yesterday,
        "tomorrow": tomorrow,
        "date": today.format('YYYY-MM-DD'),
        "counts": list(result_dict)
    }
    return jsonify(ret)


@api.route('/counthistory/', methods=['GET'], defaults={'page': 0})
@api.route('/counthistory/<page>/', methods=['GET'])
@jwt_required
@role_required(['admin', 'visitor', 'public'])
def counthistory(page):
    '''
    Count history for all shelters for the past 14 days.
    Used for chart showing counts over time.
    Supports pagination with page in path
    '''
    tz = Prefs['timezone']

    pagesize = 14  # days
    daysback = int(page) * pagesize + pagesize - 1

    today = pendulum.today(tz).subtract(days=(int(page) * pagesize))
    backthen = pendulum.today(tz).subtract(days=daysback)

    date_list = func.generate_series(
        cast(backthen.to_date_string(), Date),
        cast(today.to_date_string(), Date),
        '1 day'
    ).alias('gen_day')

    time_series = db.session.query(Shelter.name.label('label'), func.array_agg(Count.bedcount).label('data'))\
        .join(date_list, true())\
        .outerjoin(Count, (Count.day == column('gen_day')) & (Count.shelter_id == Shelter.id))\
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
    '''
    Provives a list of logs for a particular shelter
    '''
    pagesize = 15  # records
    offset = pagesize * int(page)
    shelter = Shelter.query.get_or_404(shelterid)
    total_calls = db.session.query(func.count(Log.id)).filter_by(shelter_id=shelterid).scalar()
    logs = db.session.query(Log)\
        .filter_by(shelter_id=shelterid)\
        .order_by(Log.time.desc())\
        .limit(pagesize).offset(offset)

    result = [row.toDict() for row in logs]

    return jsonify(shelter=shelter.name, logs=result, total_calls=total_calls, page_size=pagesize)


@api.route('/setcount/', methods=['POST'])
@jwt_required
@role_required(['admin'])
def set_count():
    '''
    Manually sets the count on a given day or
    delete count if personcount is empty

    Used for Admins to alter mistakes from callers
    '''
    params = request.get_json()

    personcount = params.get('numberOfPeople')
    shelterID = params.get('shelterID')
    day = params.get('day')

    if not all((shelterID, day)):
        return jsonify({"success": False, "error": "Missing data"}), 400

    try:
        parsed_day = pendulum.parse(day, strict=False)
    except ValueError:
        return jsonify({"success": False, "error": "Can't parse date"}), 400

    if not personcount:
        count = Count().query.filter_by(shelter_id=shelterID, day=parsed_day.isoformat()).delete()
        log = Log(
            shelter_id=shelterID,
            from_number='web',
            contact_type="Admin",
            input_text="-",
            action="delete_count",
            parsed_text="")
        ret = {"personcount": None, "bedcount": None, "shelterID": shelterID}
    else:
        shelter = Shelter.query.get(int(shelterID))
        count = Count(
            shelter_id=shelterID,
            personcount=personcount,
            bedcount=shelter.capacity - int(personcount),
            day=parsed_day.isoformat(),
            time=func.now()
        )
        log = Log(
            shelter_id=shelterID,
            from_number="web",
            contact_type="Admin",
            input_text=personcount,
            action="save_count",
            parsed_text=personcount
        )
        ret = {"personcount": count.personcount, "bedcount": count.bedcount, "shelterID": shelterID}
        db.session.merge(count)

    try:
        db.session.add(log)
        db.session.commit()
    except IntegrityError as e:             # calls has a foreign key constraint linking it to shelters
        logging.error(e.orig.args)
        db.session().rollback()
        return jsonify({"success": False, "error": "Error Saving Data"}), 500

    return jsonify({"success": True, "counts": ret})
