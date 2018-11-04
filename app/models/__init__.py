from flask_sqlalchemy import SQLAlchemy
from collections import OrderedDict
from sqlalchemy import inspect
from sqlalchemy.sql import func
import enum

db = SQLAlchemy()

class contact_types(enum.Enum):
    unknown: 1
    incoming_text: 2
    incoming_call: 3
    outgoing_call: 4

class Shelter(db.Model):
    __tablename__ = 'shelters'
    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(128), unique=True)
    login_id  = db.Column(db.String(16), unique=True)
    capacity  = db.Column(db.Integer)
    lat       = db.Column(db.Float)
    lon       = db.Column(db.Float)
    calls     = db.relationship('Call', backref='shelter')
    counts    = db.relationship('Count', backref='shelter')
    phone     = db.Column(db.String(16), unique=True)
    active    = db.Column(db.Boolean, server_default="TRUE", nullable=False)
    def toDict(self):
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}
    def __repr__(self):
        return '<Shelter %r>' % self.name

class Count(db.Model):
    __tablename__ = 'counts'
    bedcount   = db.Column(db.Integer, nullable=False)
    day        = db.Column(db.Date, primary_key=True)
    shelter_id = db.Column(db.Integer, db.ForeignKey('shelters.id'), primary_key=True)
    call_id    = db.Column(db.Integer, db.ForeignKey('calls.id'), nullable=False)
    def toDict(self):
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}

class Call(db.Model):
    __tablename__ = 'calls'
    id           = db.Column(db.Integer, primary_key=True)
    shelter_id   = db.Column(db.Integer, db.ForeignKey('shelters.id'), nullable = False)
    time         = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable = False)
    inputtext    = db.Column(db.String)
    bedcount     = db.Column(db.Integer, nullable = False)
    from_number  = db.Column(db.String(16)) 
    count        = db.relationship('Count', backref='call')
    contact_type = db.Column(db.Enum(contact_types))
    def toDict(self):
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}
