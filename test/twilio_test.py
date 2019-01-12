import pytest
from app import create_app
from testing.postgresql import Postgresql

app = create_app('testing')
@pytest.fixture
def client():
    with Postgresql() as postgresql:
        app.config['SQLALCHEMY_DATABASE_URI'] = postgresql.url()

def test_empty():
    assert True