import os
from ..models import Pref, db
from flask import Blueprint

pref_api = Blueprint('pref_api', __name__)

class __Prefs:
    ''' The __Prefs class wraps the sqlalchemy object allowing a mapping of prefs to columms
        regular key indexing should fetch and set values: p['timezone'] = "America/Anchorage"
    '''    
    def __init__(self, defaults):
        self.defaults = defaults 
    def init(self, app):
        ''' Constructor should be passed a dictionary with keys that correspond to columns in the prefs table and their 
            and their corresponding default values. This will find the row corresponding to `app_id` or create that row from the
            default values. 
         '''
        with app.app_context():
            prefs = Pref.query.get(self.defaults['app_id'])
            if prefs is None:
                prefs = Pref(**self.defaults)
                db.session.add(prefs)
                db.session.commit()
            self._prefs = prefs

    def __getitem__(self, name):
        if name not in self.defaults:
            raise KeyError
        return getattr(self._prefs, name)

    def __setitem__(self, name, value):
        if name not in self.defaults:
            raise KeyError
        setattr(self._prefs, name, value)
        db.session.add(self._prefs)
        db.session.commit()
   
    def update(self, d):
        for k in d:
            if k not in self.defaults:
                raise KeyError(k)
            setattr(self._prefs, k, d[k])
        db.session.add(self._prefs)
        db.session.commit()

    def toDict(self):
        return self._prefs.toDict()
   
   
preference_defaults = {
    "app_id": os.environ['APP_NAME'],
    "timezone": os.environ.get('PEND_TZ'),
    "enforce_hours": True,
    "open_time": os.environ.get('OPEN'),
    "close_time": os.environ.get('CLOSED'),
    "start_day": os.environ.get('DAY_CUTOFF')
}

Prefs = __Prefs(preference_defaults)

from . import views
