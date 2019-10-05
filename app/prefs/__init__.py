import os
from ..models import Pref, db
from flask import Blueprint

pref_api = Blueprint('pref_api', __name__)

class __Prefs:
    ''' 
   The __Prefs class wraps the sqlalchemy object allowing a mapping of prefs to columms
   Regular key indexing should fetch and set values: p['timezone'] = "America/Anchorage"
    '''    
    def init(self, app):
        ''' 
        This will find the row corresponding to `app_id` or create that row from the
        default values. This is done as a seperate method to allow easy testing while still 
        using a singleton prefs object. 
        '''
        self.defaults = defaults()
        with app.app_context():
            prefs = Pref.query.get(self.defaults['app_id'])
            if prefs is None:
                prefs = Pref(**self.defaults)
                db.session.add(prefs)
                db.session.commit()

    def __getitem__(self, name):
        if name not in self.defaults:
            raise KeyError
        #return getattr(self._prefs, name)
        prefs = Pref.query.get(self.defaults['app_id'])
        return getattr(prefs, name)

    def __setitem__(self, name, value):
        if name not in self.defaults:
            raise KeyError
        prefs = Pref.query.get(self.defaults['app_id'])
        setattr(prefs, name, value)
        db.session.add(prefs)
        db.session.commit()
   
    def update(self, d):
        prefs = Pref.query.get(self.defaults['app_id'])
        for k in d:
            if k not in self.defaults:
                raise KeyError(k)
            setattr(prefs, k, d[k])
        db.session.add(prefs)
        db.session.commit()

    def toDict(self):
        prefs = Pref.query.get(self.defaults['app_id'])
        return prefs.toDict()
   
def defaults():   
    return  {
        "app_id": os.environ['APP_NAME'],
        "timezone": os.environ.get('PEND_TZ'),
        "enforce_hours": True,
        "open_time": os.environ.get('OPEN'),
        "close_time": os.environ.get('CLOSED'),
        "start_day": os.environ.get('DAY_CUTOFF')
    }

Prefs = __Prefs()

from . import views
