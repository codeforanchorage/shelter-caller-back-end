from datetime import date, timedelta
import pytest
from app import db
from app.models import Count, Shelter

fake_counts = [
    {
        'bedcount': 100,
        'personcount': 20,
        'day': date.today().isoformat(),
        'shelter_id': 1
    },
    {
        'bedcount': 31,
        'personcount': 20,
        'day': (date.today() - timedelta(days=1)).isoformat(),
        'shelter_id': 1
    },
    {
        'bedcount': 32,
        'personcount': 10,
        'day': (date.today() - timedelta(days=1)).isoformat(),
        'shelter_id': 2
    }
]


@pytest.fixture
def counts(client, test_shelters):
    for s in test_shelters:
        db.session.add(Shelter(**s))
    for count in fake_counts:
        db.session.add(Count(**count))
    db.session.commit()
