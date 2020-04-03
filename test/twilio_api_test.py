import pytest
import json
import pendulum
from unittest.mock import patch
from app import db
from app.prefs import Prefs
from app.models import Shelter, Log, Count
import urllib.request
import urllib.parse

from . import environ

test_shelter = {
    "id": 99,
    'name': "test_shelter",
    'login_id': '9999',
    'capacity': 100,
    'phone': '123-555-5555',
    'active': True,
}

inactive_shelter = {
    "id": 98,
    'name': "inactive shelter",
    'login_id': '1111',
    'capacity': 100,
    'phone': '123-222-2222',
    'active': False,
}

test_shelter3 = {
    "id": 97,
    'name': "test_shelter_3",
    'login_id': '0000',
    'capacity': 100,
    'phone': '123-111-1111',
    'active': True,
}

shelter_no_number = {
    "id": 96,
    'name': "Uncallable",
    'login_id': '9696',
    'capacity': 150,
    'phone': None,
    'active': True,
}
shelter_empty_number = {
    "id": 95,
    'name': "Uncallable2",
    'login_id': '9595',
    'capacity': 110,
    'phone': "",
    'active': True,
}
twil_url = environ['TWILIO_FLOW_BASE_URL'] + environ['TWILIO_FLOW_ID'] + '/Executions'


def getDataRoute(shelter):
    return {"To": shelter['phone'], "From": "+19073121978", "Parameters": '{"id":"%d"}' % shelter['id']}


##########################
#       start_call       #
##########################
@patch('urllib.request.urlopen')
def test_start_call(mockObj, app_with_envion_DB):
    '''It should call the url to initiate the Twilio flow with the correct data'''
    s = Shelter(**test_shelter)
    db.session.add(s)
    db.session.commit()

    client = app_with_envion_DB.test_client()
    client.get('/twilio/start_call/')

    mockObj.assert_called_with(twil_url, urllib.parse.urlencode(getDataRoute(test_shelter)).encode())


@patch('urllib.request.urlopen')
def test_start_call_inactive(mockObj, app_with_envion_DB):
    '''It should not call the url to initiate the Twilio flow for inactive shelters'''
    s2 = Shelter(**inactive_shelter)
    db.session.add(s2)
    db.session.commit()

    client = app_with_envion_DB.test_client()
    client.get('/twilio/start_call/')

    mockObj.assert_not_called()


@patch('urllib.request.urlopen')
def test_start_call_multiple(mockObj, app_with_envion_DB):
    '''It should call the url to initiate the Twilio flow with the correct data for each active shelter'''
    s = Shelter(**test_shelter)
    db.session.add(s)
    s2 = Shelter(**inactive_shelter)
    db.session.add(s2)
    s3 = Shelter(**test_shelter3)
    db.session.add(s3)
    db.session.commit()
    client = app_with_envion_DB.test_client()
    client.get('/twilio/start_call/')

    assert mockObj.call_count == 2
    mockObj.assert_any_call(twil_url, urllib.parse.urlencode(getDataRoute(test_shelter)).encode())
    mockObj.assert_any_call(twil_url, urllib.parse.urlencode(getDataRoute(test_shelter3)).encode())


@patch('urllib.request.urlopen')
def test_start_call_empty_number(mockObj, app_with_envion_DB):
    '''It should not try to call shelters with undefined or empty numbers'''
    s = Shelter(**test_shelter)
    db.session.add(s)
    s2 = Shelter(**shelter_no_number)
    db.session.add(s2)
    s3 = Shelter(**test_shelter3)
    db.session.add(s3)
    s4 = Shelter(**shelter_empty_number)
    db.session.add(s4)

    db.session.commit()

    client = app_with_envion_DB.test_client()
    client.get('/twilio/start_call/')

    assert mockObj.call_count == 2
    mockObj.assert_any_call(twil_url, urllib.parse.urlencode(getDataRoute(test_shelter)).encode())
    mockObj.assert_any_call(twil_url, urllib.parse.urlencode(getDataRoute(test_shelter3)).encode())


@patch('urllib.request.urlopen')
def test_log_start_call(mockObj, app_with_envion_DB):
    '''Outgoing calls should make a log entry'''
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
def test_start_call_existing(pend_mock, urlopen_mock, app_with_envion_DB):
    '''It should only initiate calls when an existing count is not in the DB for a given date and shelter id'''
    s = Shelter(**test_shelter)
    db.session.add(s)
    s3 = Shelter(**test_shelter3)
    db.session.add(s3)

    today = '2019-05-21T22:00:00'
    pend_mock.return_value = today
    count = Count(shelter_id=test_shelter['id'], personcount=100, bedcount=5, day=today, time=today)
    db.session.add(count)
    db.session.commit()
    client = app_with_envion_DB.test_client()
    client.get('/twilio/start_call/')

    urlopen_mock.assert_called_once_with(twil_url, urllib.parse.urlencode(getDataRoute(test_shelter3)).encode())


@patch('urllib.request.urlopen')
@patch('pendulum.today')
def test_start_call_return_true(pend_mock, urlopen_mock, app_with_envion_DB):
    '''It should return a true JSON result when there are no shelters to call'''
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
def test_start_call_return_false(urlopen_mock, app_with_envion_DB):
    '''It should return a 449 status code when there were shelters to call'''
    s = Shelter(**test_shelter)
    db.session.add(s)
    db.session.commit()
    client = app_with_envion_DB.test_client()
    rv = client.get('/twilio/start_call/')
    assert rv.status_code == 449


##########################
#    validate_shelter    #
##########################
def test_validate_shelter_good(app_with_envion_DB):
    ''' Should return the shelter data given a known pip '''
    s = Shelter(**test_shelter)
    db.session.add(s)
    s3 = Shelter(**test_shelter3)
    db.session.add(s3)

    db.session.commit()
    data = {'shelterID': test_shelter['login_id']}
    client = app_with_envion_DB.test_client()

    rv = client.post('/twilio/validate_shelter/', data=data)
    res = json.loads(rv.data)
    assert res['success'] == True
    assert res['id'] == test_shelter['id']
    assert res['name'] == test_shelter['name']


def test_validate_shelter_bad(app_with_envion_DB):
    ''' Should not return the shelter data given a known pip '''
    s = Shelter(**test_shelter)
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
@pytest.mark.current
@patch('pendulum.now')
def test_validate_time_before_midnight(pend_mock, app_with_envion_DB):
    ''' Before midnight it should add a row to the count table with day value set to tomorrow and correct counts'''
    date = '2019-05-20'
    tomorrow = '2019-05-21'
    time = pendulum.parse(date + 'T' + Prefs['start_day'], tz=Prefs['timezone']).add(minutes=1)
    pend_mock.return_value = time

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


@pytest.mark.current
@patch('pendulum.now')
def test_validate_time_before_cutoff(pend_mock, app_with_envion_DB):
    ''' Should add a row to the count table with day value set today if before the cuttoff '''
    date = '2019-05-20'
    time = pendulum.parse(date + 'T' + Prefs['start_day'], tz=Prefs['timezone']).subtract(minutes=1)
    pend_mock.return_value = time

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


@pytest.mark.current
@patch('pendulum.now')
def test_validate_time_after_midnight(pend_mock, app_with_envion_DB):
    ''' Should set correct day (the current day) when call happens after midnight '''
    Prefs['start_day'] = "23:00"
    date = '2019-05-20'
    time = pendulum.parse(date + 'T' + '01:00', tz=Prefs['timezone'])
    pend_mock.return_value = time

    s = Shelter(**test_shelter)
    db.session.add(s)
    db.session.commit()
    data = {'numberOfPeople': 90, 'shelterID': test_shelter['id']}
    client = app_with_envion_DB.test_client()

    rv = client.post('/twilio/save_count/', data=data)
    json.loads(rv.data)
    count = db.session.query(Count).one()
    assert str(count.day) == date


@pytest.mark.current
@patch('pendulum.now')
def test_validate_time_log(pend_mock, app_with_envion_DB):
    ''' Should enter a row in the log when saving a count '''
    date = '2019-05-20'
    phone = '123-555-5555'
    time = pendulum.parse(date + 'T' + '01:00', tz=Prefs['timezone'])
    pend_mock.return_value = time

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
