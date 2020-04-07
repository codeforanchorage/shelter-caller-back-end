import pendulum
from pendulum.exceptions import ParserError
from sqlalchemy import Date
from sqlalchemy.sql import func, column
from sqlalchemy.sql.expression import cast, true
from . import api

from flask import jsonify
from ..models import db, Shelter, Count
from ..prefs import Prefs

##################
#     Counts     #
##################
@api.route('/pub_counts/', defaults={'datestring': None}, methods=['GET'])
@api.route('/pub_counts/<datestring>', methods=['GET'])
def public_counts(datestring):
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
        Count.personcount,
        Count.day,
        Count.time)\
        .filter(Count.day == today.isoformat(' '))\
        .subquery()

    shelterQuery = db.session.query(Shelter.name, Shelter.description, Shelter.id, count_calls)

    counts = shelterQuery\
        .outerjoin(count_calls, (Shelter.id == count_calls.c.call_shelterID))\
        .filter(Shelter.visible == True, Shelter.public)\
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
