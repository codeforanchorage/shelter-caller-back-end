import os
from flask_csv import send_csv
import logging
import pendulum
from pendulum.exceptions import ParserError
from sqlalchemy import Date
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import cast, true
from sqlalchemy.sql import func, column
from . import api

from flask import request, jsonify, g
from flask_jwt_simple import jwt_required, create_jwt, jwt_optional
from .forms import newShelterForm
from ..models import db, Shelter, Count, Log, User
from ..prefs import Prefs
from .decorators import role_required, add_user
from app.exceptions import InvalidUsage, UnauthorizedUse, ServerError

# TODO write a real solution for this
# This is just a stopgap to get csv with tokens working
TEMP_API_KEY = os.environ['TEMP_EXPORT_KEY']
TEMP_PUBLIC_EXPORT_KEY = os.environ['TEMP_PUBLIC_EXPORT_KEY']


##############
#    AUTH    #
##############
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
        raise InvalidUsage("Missing JSON in request")

    params = request.get_json()
    user = params.get('user', None)
    password = params.get('password', None)

    if not user:
        raise InvalidUsage("Missing username parameter")
    if not password:
        raise InvalidUsage("Missing password paramter")

    db_user = User.query.filter_by(username=user).first()
    if not db_user or db_user.password != password:
        raise UnauthorizedUse()
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
        204:
    '''
    Shelter.query.filter_by(id=shelter_id).delete()
    db.session.commit()
    return '', 204


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
    shelter['public'] = form.public.data

    shelter = Shelter(**shelter)

    try:
        shelter = db.session.merge(shelter)
        db.session.commit()
    except IntegrityError as e:
        logging.warning(e.orig.args)
        db.session().rollback()
        raise InvalidUsage("Values must be unique", status_code=400)
    return jsonify(shelter.toDict())


##################
#     Counts     #
##################
@api.route('/counts/', defaults={'datestring': None}, methods=['GET'])
@api.route('/counts/<datestring>', methods=['GET'])
@jwt_optional
@add_user()
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
    except (ParserError, TypeError):
        today = now

    # help browsers navigate dates without worring about local timezone
    yesterday = today.subtract(days=1).format('YYYYMMDD')
    if today < now:
        tomorrow = today.add(days=1).format('YYYYMMDD')
    else:
        tomorrow = None

    count_calls = db.session.query(
        Count.shelter_id.label("call_shelterID"),
        Count.bedcount,
        Count.personcount,
        Count.day,
        Count.time)\
        .filter(Count.day == today.isoformat(' '))\
        .subquery()

    # Only admins and visitors see percentages
    if 'user' not in g or set(['admin', 'visitor']).isdisjoint(set([role.name for role in g.user.roles])):
        shelterQuery = db.session.query(Shelter.name, Shelter.description, Shelter.id, count_calls)
    else:
        shelterQuery = db.session.query(Shelter.name, Shelter.description, Shelter.capacity, Shelter.id, count_calls)

    counts = shelterQuery\
        .outerjoin(count_calls, (Shelter.id == count_calls.c.call_shelterID))

    if 'user' in g and 'admin' in [role.name for role in g.user.roles]:
        counts = counts.filter(Shelter.visible == True)
    else:
        counts = counts.filter(Shelter.visible == True, Shelter.public)

    counts = counts.order_by(Shelter.name)

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
@jwt_optional
@add_user()
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

    time_series = db.session.query(Shelter.name.label('label'), func.array_agg(Count.personcount).label('data'))\
        .join(date_list, true())\
        .outerjoin(Count, (Count.day == column('gen_day')) & (Count.shelter_id == Shelter.id))

    if 'user' not in g or set(['admin', 'visitor']).isdisjoint(set([role.name for role in g.user.roles])):
        time_series = time_series.filter(Shelter.visible == True, Shelter.public)
    else:
        time_series = time_series.filter(Shelter.visible == True)

    time_series = time_series\
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
        raise InvalidUsage("Missing data", status_code=400)
    try:
        parsed_day = pendulum.parse(day, strict=False)
    except ValueError:
        raise InvalidUsage("Can't parse date", status_code=400)

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
        raise ServerError('Error Saving Data')

    return jsonify({"success": True, "counts": ret})

# The following two routes are quick stopgaps for allowing api data to be accessed
# With a token rather than a login
# TODO: make this more flexible and pull tokens from DB rather than env.
@api.route(f'/{TEMP_API_KEY}/export/', methods=['GET'])
def export():
    '''
    Returns all counts per shelter
    Returns:
        200:
            JSON object with:
                counts: list of shelters and this day's counts
    '''

    # only show person count to admin
    counts = db.session.query(Count)\
        .join(Shelter, Shelter.id == Count.shelter_id)\
        .order_by(Count.day)\
        .values(
            Count.shelter_id,
            Count.bedcount,
            Count.personcount,
            Count.day,
            Shelter.name
    )

    result_dict = map(lambda q: q._asdict(), counts)

    return send_csv(result_dict, "shelterCounts.csv", ['day', 'name', 'personcount', 'bedcount', 'shelter_id'])


@api.route(f'/{TEMP_PUBLIC_EXPORT_KEY}/export/', methods=['GET'])
def export_public():
    '''
    Returns all counts per shelter for public shelters
    Returns:
        200:
            JSON object with:
                counts: list of shelters and this day's counts
    '''

    # only show person count to admin
    counts = db.session.query(Count)\
        .join(Shelter, Shelter.id == Count.shelter_id)\
        .order_by(Count.day)\
        .filter(Shelter.public)\
        .values(
            Count.shelter_id,
            Count.bedcount,
            Count.personcount,
            Count.day,
            Shelter.name
    )

    result_dict = map(lambda q: q._asdict(), counts)

    return send_csv(result_dict, "shelterCounts.csv", ['day', 'name', 'personcount', 'bedcount', 'shelter_id'])


@api.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@api.errorhandler(UnauthorizedUse)
def handle_unauthorized_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response
