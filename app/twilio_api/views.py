from . import twilio_api
import logging
import urllib.request
import urllib.parse
import pendulum
from flask import request, jsonify, Response
from sqlalchemy import Date
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import cast, func
import re
import os
from ..models import Shelter, db, Count, Log

tz = os.environ['PEND_TZ'] 

def fail(reason, tries):
    return jsonify({"success": False, "error": reason, "tries": tries})

def commitLog(log):
    try:
        db.session.add(log)                # TODO it would be nicer if we could use Postgres's ON CONFLICT…UPDATE
        db.session.commit()
    except IntegrityError as e:            # calls has a foreign key constraint linking it to shelters
        logging.error(e.orig.args)
        db.session().rollback()

# Twilio flow enpoint requires basic auth with a user/password found in the Twilio account settings
password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
password_mgr.add_password(None, os.environ['TWILIO_FLOW_BASE_URL'], os.environ['TWILIO_USERNAME'], os.environ['TWILIO_PASSWORD']) 
handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
opener = urllib.request.build_opener(handler)

urllib.request.install_opener(opener)

@twilio_api.route('/start_call/', methods = ['GET'])
def startcall():
    ''' Cron calls this end point to start the flow for each number that hasn't been contacted today'''     
    flowURL = os.environ['TWILIO_FLOW_BASE_URL']+os.environ['TWILIO_FLOW_ID']+"/Executions"

    today = pendulum.today(os.environ['PEND_TZ'])
    uncontacted = Shelter.query.outerjoin(Count, (Count.shelter_id == Shelter.id) & (Count.day == cast(today, Date))).filter((Count.day == None) & (Shelter.active == True))

    # we have reached all shetlers return success
    if uncontacted.count() == 0:
        return jsonify({"success": True})

    for shelter in uncontacted:
        print(f"calling:{shelter.phone}")

        id = shelter.id
        route = {"To" : shelter.phone, "From" : "+19073121978", "Parameters": f'{{"id":"{id}"}}'}
        data = urllib.parse.urlencode(route).encode()

        with urllib.request.urlopen(flowURL, data) as f:
            logging.info("Twilio Return Code: %d" % f.getcode())

        log = Log(shelter_id=id, from_number='+19073121978', contact_type='outgoing_call', action="initialize call" )
        db.session.add(log)
        db.session.commit()

    return Response("Not all shelters contacted", status=503 )

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

@twilio_api.route('/validate_shelter/', methods = ['POST'])
def validateshelter():
    ''' Allows calls/texts from different phones to identify themselves and report.
        If the shelterID does not match a login_id in the shelters table it will fail
        Otherwise it should return info about the shelter, especially the primary key which will be used later
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
    # beds will be defined if a user keyed in a number
    # text will be defined if the user said something

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
        today = pendulum.today(os.environ['PEND_TZ'])
        shelter = Shelter.query.get(int(shelterID))
        count = Count(shelter_id=shelterID, personcount=personcount, bedcount = shelter.capacity - int(personcount), day=today.isoformat(' '), time=func.now())

        log = Log(shelter_id=shelterID, from_number=fromPhone, contact_type=contact_type, input_text=input, action="save_count", parsed_text=personcount)

        try:
            db.session.merge(count)             # TODO it would be nicer if we could use Postgres's ON CONFLICT…UPDATE
            db.session.add(log)
            db.session.commit()
        except IntegrityError as e:             # calls has a foreign key constraint linking it to shelters
            logging.error(e.orig.args)
            db.session().rollback()
            return fail("Could not record call because of database error", tries + 1)

        return  jsonify({"success": True})

    log = Log(shelter_id=shelterID, from_number=fromPhone, contact_type=contact_type, input_text=input, error="bad input",  action="save_count", parsed_text=personcount)
    try:
        db.session.add(log)
        db.session.commit()
    except IntegrityError as e:             # calls has a foreign key constraint linking it to shelters
        logging.error(e.orig.args)
        db.session().rollback()

    return fail('Required parameters missing', tries + 1)
