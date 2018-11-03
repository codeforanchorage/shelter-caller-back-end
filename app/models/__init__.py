from flask_sqlalchemy import SQLAlchemy
from collections import OrderedDict
from sqlalchemy import inspect
from sqlalchemy.sql import func

db = SQLAlchemy()

class Shelter(db.Model):
    __tablename__ = 'shelters'
    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(128), unique=True)
    login_id  = db.Column(db.String(16), unique=True)
    capacity  = db.Column(db.Integer)
    lat       = db.Column(db.Float)
    lon       = db.Column(db.Float)
    calls     = db.relationship('Call', backref='shelter')
    phone     = db.Column(db.String(16), unique=True)
    active    = db.Column(db.Boolean, server_default="TRUE", nullable=False)
    def toDict(self):
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}
    def __repr__(self):
        return '<Shelter %r>' % self.name

class Call(db.Model):
    __tablename__ = 'calls'
    id          = db.Column(db.Integer, primary_key=True)
    shelter_id  = db.Column(db.Integer, db.ForeignKey('shelters.id'), nullable = False)
    time        = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable = False)
    bedcount    = db.Column(db.Integer, nullable = False)
    from_number = db.Column(db.String(16)) 
    def toDict(self):
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}
