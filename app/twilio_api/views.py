from . import twilio_api
from ..models import Shelter, db, Count, Log
from ..prefs import Prefs
import logging
import os
import pendulum
import re
import urllib.request
import urllib.parse
from flask import request, jsonify, Response
from sqlalchemy import Date
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import cast, func


def saytime(pendObj):
    '''Function to convert times into sayable phrases'''
    hour = pendObj.hour
    ampm = "P M" if hour >= 12 else "A M"
    hour = 12 if hour % 12 == 0 else hour % 12
    
    minute = pendObj.minute
    if minute == 0:
        minute = "O'clock"
    elif minute < 10:
        minute = f"oh {minute}"
    return f"{hour} {minute} {ampm}"


def fail(reason, tries):
    return jsonify({"success": False, "error": reason, "tries": tries})

def commitLog(log):
    try:
        db.session.add(log)
        db.session.commit()
    except IntegrityError as e:
        logging.error(e.orig.args)
        db.session().rollback()

# Set up basic auth with a user/password for Twilio API
password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()

password_mgr.add_password(None, 
   os.environ['TWILIO_FLOW_BASE_URL'],
   os.environ['TWILIO_USERNAME'],
   os.environ['TWILIO_PASSWORD']) 

handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
opener = urllib.request.build_opener(handler)
urllib.request.install_opener(opener)

@twilio_api.route('/start_call/', methods = ['GET'])
def startcall():
    ''' 
    Cron calls this end point to start the flow 
    for each number that hasn't been contacted today
    '''
    flowURL = os.environ['TWILIO_FLOW_BASE_URL']+os.environ['TWILIO_FLOW_ID']+"/Executions"

    today = pendulum.today(Prefs['timezone'])
    if pendulum.now(Prefs['timezone']).time() > pendulum.parse(Prefs['start_day'], tz=Prefs['timezone']).time():
            today = today.add(days=1)

    '''
    -- get all shelters where there is no count for today. SQL:
        SELECT * FROM shelters
        LEFT OUTER JOIN counts ON counts.shelter_id = shelters.id AND counts.day = CAST(%(param_1)s AS DATE) 
        WHERE counts.day IS NULL AND shelters.active = true AND shelters.phone IS NOT NULL AND shelters.phone != %(phone_1)s
    '''
    uncontacted = Shelter.query.outerjoin(Count, 
      (Count.shelter_id == Shelter.id) 
      & (Count.day == cast(today, Date))).filter((Count.day == None) & (Shelter.active == True) & (Shelter.phone != None) & (Shelter.phone != ''))

    if uncontacted.count() == 0:
        return jsonify({"success": True})

    for shelter in uncontacted:
        id = shelter.id
        route = {"To": shelter.phone, 
                 "From": "+19073121978", 
                 "Parameters": f'{{"id":"{id}"}}'}

        data = urllib.parse.urlencode(route).encode()

        with urllib.request.urlopen(flowURL, data) as f:
            logging.info("Twilio Return Code: %d" % f.getcode())

        log = Log(shelter_id=id, 
                  from_number = '+19073121978',
                  contact_type = 'outgoing_call',
                  action = "initialize call" )

        db.session.add(log)
        db.session.commit()

    return Response("Not all shelters contacted", status=449 )

@twilio_api.route('/log_failed_call/', methods = ['POST'])
def logFailedCall():
    '''Records a failure in the calls table'''
    error         = request.form.get('error')
    fromPhone     = request.form.get('phone')
    contact_type  = request.form.get('contactType') or 'unknown'
    shelterID     = request.form.get('shelterID') 

    log = Log(shelter_id=shelterID, from_number=fromPhone, contact_type=contact_type, error=error)
    try:
        db.session.add(log)                # TODO it would be nicer if we could use Postgres's ON CONFLICT…UPDATE
        db.session.commit()
    except IntegrityError as e:            #  calls has a foreign key constraint linking it to shelters
        logging.error(e.orig.args)
        db.session().rollback()
        return fail("Could not record call because of database error", 1)
        
    return  jsonify({"success": True})

@twilio_api.route('/validate_time/', methods = ['GET'])
def validate_time():
    '''The app should only accept input during certain hours. This will return true of false depending 
       on whether the current time is within the open hours
    '''
    start = pendulum.parse(Prefs['open_time'], tz=Prefs['timezone']).time()
    end   = pendulum.parse(Prefs['close_time'], tz=Prefs['timezone']).time()
    now   = pendulum.now(Prefs['timezone']).time()
    openHours_speech = f"between {saytime(start)} and {saytime(end)}"
    text_hours = f"between {start.format('h:mm A')} and {end.format('h:mm A')}"
    
    if Prefs['enforce_hours']:
        if start < end:
            return jsonify({"open": start < now < end, "hours": text_hours, "spoken_hours": openHours_speech})
        else: # time spans midnight
            return jsonify({"open":  now < end or now > start, "hours": text_hours, "spoken_hours": openHours_speech})
    else:
        return jsonify({"open": True})

@twilio_api.route('/validate_shelter/', methods = ['POST'])
def validateshelter():
    ''' Allows calls/texts from different phones to identify themselves and report.
        If the shelterID does not match a login_id in the shelters table it will fail
        Otherwise it should return info about the shelter, 
        especially the primary key which will be used later
    '''
    shelterID    = request.form.get('shelterID_retry') or request.form.get('shelterID')
    text         = request.form.get('spokenText')
    fromPhone    = request.form.get('phone')
    contact_type = request.form.get('contactType')
    tries        = int(request.form.get('tries', 0) or 0)
    input = shelterID
 
    if not shelterID: 
        input = text
        numbers = re.findall('[\d|\s]+', text)
        # spoken text may showup with spaces such as "1 2 1 3 "
        if len(numbers) == 1:
            shelterID = numbers[0].replace(" ", "")
    
    shelter = Shelter.query.filter_by(login_id=shelterID).first()

    if shelter:
        log = Log(shelter_id=shelter.id, from_number=fromPhone, contact_type=contact_type, input_text=input, parsed_text=shelterID, action="validate_shelter")
        commitLog(log)
        return jsonify({"success": True, "id":shelter.id, "login_id":shelter.login_id, "name":shelter.name})
    else:
        log = Log(from_number=fromPhone, contact_type=contact_type, input_text=input, parsed_text=shelterID, error="invalid shelter id", action="validate_shelter")
        commitLog(log)
        return fail("Could not identify shelter", tries + 1)


@twilio_api.route('/save_count/', methods = ['POST'])
def collect():
    ''' 
    Twilio calls this endpoint
    Make entry into db indicating today's numbers.
    Also mark this shelter as being succesfully contacted
    It will return a json response {"success": [true | false]} depening on whether it understood the user
    '''
    # numberOfPeople will be defined if a user keyed in a number
    # spokenText will be defined if the user said something

    input         = request.form.get('numberOfPeople')
    text          = request.form.get('spokenText')
    fromPhone     = request.form.get('phone')
    shelterID     = request.form.get('shelterID') 
    contact_type  = request.form.get('contactType') or 'unknown'
    tries         = int(request.form.get('tries', 0) or 0)

    personcount = None
    # TODO this trusts that shelterID has been validated by an earlier request. 
    if input:
        personcount = input
    elif text:     # try spoken text, but only if there's a single number in the response
        numbers = re.findall('\d+', text)
        input = text
        if len(numbers) == 1:
            personcount = numbers[0]
    if personcount and personcount.isdigit() and shelterID:        
        today = pendulum.today(Prefs['timezone'])
        # set the cutoff where calls count toward the next day
        if pendulum.now(Prefs['timezone']).time() > pendulum.parse(Prefs['start_day'], tz=Prefs['timezone']).time():
            today = today.add(days=1)

        shelter = Shelter.query.get(int(shelterID))
        # TODO handle error if shelter is not found
        count = Count(shelter_id=shelterID, personcount=personcount, bedcount = shelter.capacity - int(personcount), day=today.isoformat(), time=func.now())

        log = Log(shelter_id=shelterID, from_number=fromPhone, contact_type=contact_type, input_text=input, action="save_count", parsed_text=personcount)

        try:
            db.session.merge(count)             # TODO it would be nicer if we could use Postgres's ON CONFLICT…UPDATE
            db.session.add(log)
            db.session.commit()
        except IntegrityError as e:             # calls has a foreign key constraint linking it to shelters
            logging.error(e.orig.args)
            db.session().rollback()
            return fail("Could not record call because of database error", tries + 1)

        return  jsonify({"success": True, "count":personcount})

    log = Log(shelter_id=shelterID, from_number=fromPhone, contact_type=contact_type, input_text=input, error="bad input",  action="save_count", parsed_text=personcount)
    try:
        db.session.add(log)
        db.session.commit()
    except IntegrityError as e:             # calls has a foreign key constraint linking it to shelters
        logging.error(e.orig.args)
        db.session().rollback()

    return fail('Required parameters missing', tries + 1)
