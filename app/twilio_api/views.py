from . import twilio_api
import logging
import urllib.request
import urllib.parse
import pendulum
from flask import request, jsonify, Response
from sqlalchemy.exc import IntegrityError
import re
import os
from ..models import Shelter, Call, db, Count, contact_types

tz = os.environ['PEND_TZ'] 

def fail(reason=None):
    return jsonify({"success": False, "error": reason})

# Twilio flow enpoint requires basic auth with a user/password found in the Twilio account settings
password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
password_mgr.add_password(None, os.environ['TWILIO_FLOW_BASE_URL'], os.environ['TWILIO_USERNAME'], os.environ['TWILIO_PASSWORD']) 
handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
opener = urllib.request.build_opener(handler)

urllib.request.install_opener(opener)

@twilio_api.route('/start_call/', methods = ['POST'])
def startcall():
    ''' Cron calls this end point to start the flow for each number that hasn't been contacted today'''     
    flowURL = os.environ['TWILIO_FLOW_BASE_URL']+os.environ['TWILIO_FLOW_ID']+"/Executions"

    today = pendulum.today(os.environ['PEND_TZ'])
    uncontacted = Shelter.query.outerjoin(Call, (Call.shelter_id == Shelter.id) & (Call.time > today)).filter(Call.id == None)

    # we have reached all shetlers return success
    if uncontacted.count() == 0:
        return jsonify({"success": True})

    #for row in uncontacted:
    #    print(row.name, row.phone)
    # select * from shelters left outer join calls on (calls.shelter_id = shelters.id and calls.time > '2018-11-01') where calls.id IS NULL;
    for shelter in uncontacted:
        print(f"calling:{shelter.phone}")
        id = shelter.id
        route = {"To" : shelter.phone, "From" : "+19073121978", "Parameters": f'{{"id":"{id}"}}'}
        data = urllib.parse.urlencode(route).encode()

        with urllib.request.urlopen(flowURL, data) as f:
            logging.warning("Code: %d" % f.getcode())
    return Response("Not all shelters contacted", status=503 )



@twilio_api.route('/validate_shelter/', methods = ['POST'])
def validateshelter():
    ''' Allows calls/texts from different phones to identify themselves and report.
        If the shelterID does not match a login_id in the shelters table it will fail
        Otherwise it should return info about the shelter, especially the primary key which will be used later
    '''
    shelterID = request.form.get('shelterID_retry') or request.form.get('shelterID')
    text      = request.form.get('spokenText')
    fromPhone = request.form.get('phone')

    if not shelterID:
        numbers = re.findall('\d+', text)
        if len(numbers) == 1:
            shelterID = numbers[0]
    
    shelter = Shelter.query.filter_by(login_id=shelterID).first()

    if shelter:
        return jsonify({"success": True, "id":shelter.id, "login_id":shelter.login_id, "name":shelter.name})
    else:
        return fail("Could not identify shelter")


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

    input         = request.form.get('numberOfBeds')
    text          = request.form.get('spokenText')
    fromPhone     = request.form.get('phone')
    shelterID     = request.form.get('shelterID') 
    contact_type  = request.form.get('contactType') or 'unknown'

    bedcount = None
    # TODO this trusts that shelterID has been validated by an earlier request. 
    if input:
        bedcount = input
    elif text:     # try spoken text, but only if there's a single number in the response
        numbers = re.findall('\d+', text)
        input = text
        if len(numbers) == 1:
            bedcount = numbers[0]
    if bedcount and bedcount.isdigit() and shelterID:
        logging.warn("%s beds from %s: %s" % (bedcount, shelterID, fromPhone))
        
        today = pendulum.today(os.environ['PEND_TZ'])
        
        call = Call(shelter_id=shelterID, bedcount=bedcount, inputtext=input, from_number=fromPhone, contact_type=contact_type)
        count = Count(call = call, shelter_id=shelterID, bedcount=bedcount, day=today.isoformat(' '))
        try:
            db.session.merge(count)             # TODO it would be nicer if we could use Postgres's ON CONFLICT…UPDATE
            db.session.commit()
        except IntegrityError as e:             # calls has a foreign key constraint linking it to shelters
            logging.error(e.orig.args)
            db.session().rollback()
            return fail("Could not record call because of database error")

        return  jsonify({"success": True})

    return fail('Required parameters missing')
