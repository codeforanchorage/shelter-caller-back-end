import os
from app import create_app
from app.models import db
from flask_migrate import Migrate

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

migrate = Migrate(app, db)
@app.shell_context_processor
def make_shell_context():
    return dict(db=db)