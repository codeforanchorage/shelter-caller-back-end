import json
import pendulum
from unittest.mock import patch
from app import db
from app.prefs import Prefs
from app.models import Shelter, Log, Count
import urllib.request
import urllib.parse

from .fixtures.app_fixtures import environ

twil_url = environ['TWILIO_FLOW_BASE_URL'] + environ['TWILIO_FLOW_ID'] + '/Executions'


def getDataRoute(shelter):
    return {"To": shelter['phone'], "From": "+19073121978", "Parameters": '{"id":"%d"}' % shelter['id']}


##########################
#       start_call       #
##########################
@patch('urllib.request.urlopen')
def test_start_call(mockObj, app_with_envion_DB, test_shelters):
    '''It should call the url to initiate the Twilio flow with the correct data'''
    test_shelter = test_shelters[0]
    s = Shelter(**test_shelter)
    db.session.add(s)
    db.session.commit()

    client = app_with_envion_DB.test_client()
    client.get('/twilio/start_call/')

    mockObj.assert_called_with(twil_url, urllib.parse.urlencode(getDataRoute(test_shelter)).encode())


@patch('urllib.request.urlopen')
def test_start_call_inactive(mockObj, app_with_envion_DB, inactive_shelter):
    '''It should not call the url to initiate the Twilio flow for inactive shelters'''
    s2 = Shelter(**inactive_shelter)
    db.session.add(s2)
    db.session.commit()

    client = app_with_envion_DB.test_client()
    client.get('/twilio/start_call/')

    mockObj.assert_not_called()


@patch('urllib.request.urlopen')
def test_start_call_multiple(mockObj, app_with_envion_DB, inactive_shelter, test_shelters):
    '''It should call the url to initiate the Twilio flow with the correct data for each active shelter'''
    for s in test_shelters:
        db.session.add(Shelter(**s))

    s2 = Shelter(**inactive_shelter)
    db.session.add(s2)
    db.session.commit()
    client = app_with_envion_DB.test_client()
    client.get('/twilio/start_call/')

    assert mockObj.call_count == 2
    mockObj.assert_any_call(twil_url, urllib.parse.urlencode(getDataRoute(test_shelters[0])).encode())
    mockObj.assert_any_call(twil_url, urllib.parse.urlencode(getDataRoute(test_shelters[1])).encode())


@patch('urllib.request.urlopen')
def test_start_call_empty_number(mockObj, app_with_envion_DB, test_shelters, shelter_no_number, shelter_empty_number):
    '''It should not try to call shelters with undefined or empty numbers'''
    for s in test_shelters:
        db.session.add(Shelter(**s))
    s2 = Shelter(**shelter_no_number)
    db.session.add(s2)
    s4 = Shelter(**shelter_empty_number)
    db.session.add(s4)

    db.session.commit()

    client = app_with_envion_DB.test_client()
    client.get('/twilio/start_call/')

    assert mockObj.call_count == 2
    mockObj.assert_any_call(twil_url, urllib.parse.urlencode(getDataRoute(test_shelters[0])).encode())
    mockObj.assert_any_call(twil_url, urllib.parse.urlencode(getDataRoute(test_shelters[1])).encode())


@patch('urllib.request.urlopen')
def test_log_start_call(mockObj, app_with_envion_DB, test_shelters):
    '''Outgoing calls should make a log entry'''
    test_shelter = test_shelters[0]
    s = Shelter(**test_shelter)
    db.session.add(s)
    db.session.commit()

    client = app_with_envion_DB.test_client()
    client.get('/twilio/start_call/')
    logs = db.session.query(Log).one()

    assert logs.shelter_id == test_shelter['id']
    assert logs.action == "initialize call"
    assert logs.contact_type == "outgoing_call"


@patch('urllib.request.urlopen')
@patch('pendulum.today')
def test_start_call_existing(pend_mock, urlopen_mock, app_with_envion_DB, test_shelters):
    '''It should only initiate calls when an existing count is not in the DB for a given date and shelter id'''
    for s in test_shelters:
        db.session.add(Shelter(**s))

    today = '2019-05-21T22:00:00'
    pend_mock.return_value = today
    count = Count(shelter_id=test_shelters[0]['id'], personcount=100, bedcount=5, day=today, time=today)
    db.session.add(count)
    db.session.commit()
    client = app_with_envion_DB.test_client()
    client.get('/twilio/start_call/')

    urlopen_mock.assert_called_once_with(twil_url, urllib.parse.urlencode(getDataRoute(test_shelters[1])).encode())


@patch('urllib.request.urlopen')
@patch('pendulum.today')
def test_start_call_return_true(pend_mock, urlopen_mock, app_with_envion_DB, test_shelters):
    '''It should return a true JSON result when there are no shelters to call'''
    test_shelter = test_shelters[0]
    s = Shelter(**test_shelter)
    db.session.add(s)

    today = '2019-05-21T22:00:00'
    pend_mock.return_value = today
    count = Count(shelter_id=test_shelter['id'], personcount=100, bedcount=5, day=today, time=today)
    db.session.add(count)
    db.session.commit()
    client = app_with_envion_DB.test_client()
    rv = client.get('/twilio/start_call/')
    data = json.loads(rv.data)
    assert data == {"success": True}


@patch('urllib.request.urlopen')
def test_start_call_return_false(urlopen_mock, app_with_envion_DB, test_shelters):
    '''It should return a 449 status code when there were shelters to call'''
    test_shelter = test_shelters[0]
    s = Shelter(**test_shelter)
    db.session.add(s)
    db.session.commit()
    client = app_with_envion_DB.test_client()
    rv = client.get('/twilio/start_call/')
    assert rv.status_code == 449


##########################
#    validate_shelter    #
##########################
def test_validate_shelter_good(app_with_envion_DB, test_shelters):
    ''' Should return the shelter data given a known pip '''
    for s in test_shelters:
        db.session.add(Shelter(**s))

    db.session.commit()
    data = {'shelterID': test_shelters[0]['login_id']}
    client = app_with_envion_DB.test_client()

    rv = client.post('/twilio/validate_shelter/', data=data)
    res = json.loads(rv.data)
    assert res['success'] == True
    assert res['id'] == test_shelters[0]['id']
    assert res['name'] == test_shelters[0]['name']


def test_validate_shelter_bad(app_with_envion_DB, test_shelters):
    ''' Should not return the shelter data given a known pip '''

    s = Shelter(**test_shelters[0])
    db.session.add(s)
    db.session.commit()
    data = {'shelterID': '89898198'}
    client = app_with_envion_DB.test_client()

    rv = client.post('/twilio/validate_shelter/', data=data)
    res = json.loads(rv.data)
    assert res['success'] == False


#########################
#     validate_time     #
#########################
@patch('pendulum.now')
def test_validate_time_good(pend_mock, app_with_envion_DB):
    ''' If the current time is within the open-close interval it should return open = true '''
    now = pendulum.parse(Prefs['open_time'], tz=Prefs['timezone']).add(minutes=1)
    pend_mock.return_value = now
    Prefs['enforce_hours'] = True
    client = app_with_envion_DB.test_client()

    rv = client.get('/twilio/validate_time/')
    res = json.loads(rv.data)
    assert res['open'] == True


@patch('pendulum.now')
def test_validate_time_early(pend_mock, app_with_envion_DB):
    ''' If the current time is not within the open-close interval it should return open = false '''
    now = pendulum.parse(Prefs['open_time'], tz=Prefs['timezone']).subtract(minutes=1)
    pend_mock.return_value = now
    Prefs['enforce_hours'] = True
    client = app_with_envion_DB.test_client()

    rv = client.get('/twilio/validate_time/')
    res = json.loads(rv.data)
    assert res['open'] == False


@patch('pendulum.now')
def test_validate_time_late(pend_mock, app_with_envion_DB):
    ''' If the current time is not within the open-close interval it should return open = false '''
    now = pendulum.parse(Prefs['close_time'], tz=Prefs['timezone']).add(minutes=1)
    pend_mock.return_value = now
    Prefs['enforce_hours'] = True
    client = app_with_envion_DB.test_client()

    rv = client.get('/twilio/validate_time/')
    res = json.loads(rv.data)
    assert res['open'] == False


@patch('pendulum.now')
def test_validate_time_no_enforce(pend_mock, app_with_envion_DB):
    ''' It should not enforce hours when enforce flag is false'''
    now = pendulum.parse(Prefs['close_time'], tz=Prefs['timezone']).add(minutes=1)
    pend_mock.return_value = now
    Prefs['enforce_hours'] = False
    client = app_with_envion_DB.test_client()

    rv = client.get('/twilio/validate_time/')
    res = json.loads(rv.data)
    assert res['open'] == True


########################
#      save_count      #
########################
@patch('pendulum.now')
def test_validate_time_before_midnight(pend_mock, app_with_envion_DB, test_shelters):
    ''' Before midnight it should add a row to the count table with day value set to tomorrow and correct counts'''
    date = '2019-05-20'
    tomorrow = '2019-05-21'
    time = pendulum.parse(date + 'T' + Prefs['start_day'], tz=Prefs['timezone']).add(minutes=1)
    pend_mock.return_value = time
    test_shelter = test_shelters[0]

    s = Shelter(**test_shelter)
    db.session.add(s)
    db.session.commit()
    data = {'numberOfPeople': 90, 'shelterID': test_shelter['id']}
    client = app_with_envion_DB.test_client()

    rv = client.post('/twilio/save_count/', data=data)
    res = json.loads(rv.data)
    assert res['success'] == True
    count = db.session.query(Count).one()
    assert count.shelter_id == test_shelter['id']
    assert str(count.day) == tomorrow
    assert count.personcount == data['numberOfPeople']
    assert count.bedcount == test_shelter['capacity'] - data['numberOfPeople']


@patch('pendulum.now')
def test_validate_time_before_cutoff(pend_mock, app_with_envion_DB, test_shelters):
    ''' Should add a row to the count table with day value set today if before the cuttoff '''
    date = '2019-05-20'
    time = pendulum.parse(date + 'T' + Prefs['start_day'], tz=Prefs['timezone']).subtract(minutes=1)
    pend_mock.return_value = time
    test_shelter = test_shelters[0]
    s = Shelter(**test_shelter)
    db.session.add(s)
    db.session.commit()
    data = {'numberOfPeople': 90, 'shelterID': test_shelter['id']}
    client = app_with_envion_DB.test_client()

    rv = client.post('/twilio/save_count/', data=data)
    json.loads(rv.data)
    count = db.session.query(Count).one()
    assert count.shelter_id == test_shelter['id']
    assert str(count.day) == date


@patch('pendulum.now')
def test_validate_time_after_midnight(pend_mock, app_with_envion_DB, test_shelters):
    ''' Should set correct day (the current day) when call happens after midnight '''
    Prefs['start_day'] = "23:00"
    date = '2019-05-20'
    time = pendulum.parse(date + 'T' + '01:00', tz=Prefs['timezone'])
    pend_mock.return_value = time
    test_shelter = test_shelters[0]

    s = Shelter(**test_shelter)
    db.session.add(s)
    db.session.commit()
    data = {'numberOfPeople': 90, 'shelterID': test_shelter['id']}
    client = app_with_envion_DB.test_client()

    rv = client.post('/twilio/save_count/', data=data)
    json.loads(rv.data)
    count = db.session.query(Count).one()
    assert str(count.day) == date


@patch('pendulum.now')
def test_validate_time_log(pend_mock, app_with_envion_DB, test_shelters):
    ''' Should enter a row in the log when saving a count '''
    date = '2019-05-20'
    phone = '123-555-5555'
    time = pendulum.parse(date + 'T' + '01:00', tz=Prefs['timezone'])
    pend_mock.return_value = time
    test_shelter = test_shelters[0]

    s = Shelter(**test_shelter)
    db.session.add(s)
    db.session.commit()
    data = {'numberOfPeople': 80, 'shelterID': test_shelter['id'], 'phone': phone}
    client = app_with_envion_DB.test_client()

    rv = client.post('/twilio/save_count/', data=data)
    json.loads(rv.data)
    log = db.session.query(Log).one()
    assert log.shelter_id == test_shelter['id']
    assert log.from_number == phone
    assert log.parsed_text == str(data['numberOfPeople'])
