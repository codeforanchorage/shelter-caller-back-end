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
            "id": 99,
            'name': "test_shelter",
            'login_id': '9999',
            'capacity': 100,
            'phone': '123-555-5555',
            'active': True,
        },
        {
            "id": 97,
            'name': "test_shelter_3",
            'login_id': '0000',
            'capacity': 100,
            'phone': '123-111-1111',
            'active': True,
        })


@pytest.fixture
def shelter_no_number():
    return {
        "id": 96,
        'name': "Uncallable",
        'login_id': '9696',
        'capacity': 150,
        'phone': None,
        'active': True,
    }


@pytest.fixture
def shelter_empty_number():
    return {
        "id": 95,
        'name': "Uncallable2",
        'login_id': '9595',
        'capacity': 110,
        'phone': "",
        'active': True,
    }
