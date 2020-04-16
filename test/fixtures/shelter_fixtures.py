import pytest


@pytest.fixture
def inactive_shelter():
    return {
        "id": 98,
        'name': "inactive shelter",
        'login_id': '1111',
        'capacity': 100,
        'phone': '123-222-2222',
        'active': False,
    }


@pytest.fixture
def test_shelters():
    return (
        {
            "id": 1,
            'name': "test_shelter_1",
            'login_id': '9999',
            'capacity': 100,
            'phone': '907-555-1111',
            'active': True,
        },
        {
            "id": 2,
            'name': "test_shelter_2",
            'login_id': '0000',
            'capacity': 100,
            'phone': '907-555-2222',
            'active': True,
        })


@pytest.fixture
def shelter_no_number():
    return {
        "id": 101,
        'name': "Uncallable_1",
        'login_id': '9696',
        'capacity': 150,
        'phone': None,
        'active': True,
    }


@pytest.fixture
def shelter_empty_number():
    return {
        "id": 102,
        'name': "Uncallable_2",
        'login_id': '9595',
        'capacity': 110,
        'phone': "",
        'active': True,
    }
