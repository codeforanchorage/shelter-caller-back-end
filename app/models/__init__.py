from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from sqlalchemy.sql import func

db = SQLAlchemy()


class Shelter(db.Model):
    __tablename__ = 'shelters'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True)
    description = db.Column(db.String)
    login_id = db.Column(db.String(16), unique=True)
    capacity = db.Column(db.Integer)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    logs = db.relationship('Log', backref='shelter')
    counts = db.relationship('Count', backref='shelter')
    phone = db.Column(db.String(16), unique=True)
    active = db.Column(db.Boolean, server_default="TRUE", nullable=False)
    visible = db.Column(db.Boolean, server_default="TRUE")

    def toDict(self):
        return {
            c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs
        }

    def __repr__(self):
        return '<Shelter %r>' % self.name


class Count(db.Model):
    __tablename__ = 'counts'
    bedcount = db.Column(db.Integer, nullable=False)
    personcount = db.Column(db.Integer)
    day = db.Column(db.Date, primary_key=True)
    shelter_id = db.Column(
        db.Integer,
        db.ForeignKey('shelters.id', ondelete='CASCADE'),
        primary_key=True)

    time = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        server_onupdate=db.func.now())

    def toDict(self):
        return {
            c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs
        }


class Log(db.Model):
    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    shelter_id = db.Column(db.Integer, db.ForeignKey('shelters.id', ondelete='CASCADE'))
    from_number = db.Column(db.String(16))
    input_text = db.Column(db.String)
    parsed_text = db.Column(db.String)
    contact_type = db.Column(db.String)
    action = db.Column(db.String)
    error = db.Column(db.String)

    def toDict(self):
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}


class Pref(db.Model):
    '''Simple DB class for a single row holding app-specific preferences'''
    __tablename__ = 'prefs'
    app_id = db.Column(db.String, primary_key=True)
    timezone = db.Column(db.String)
    enforce_hours = db.Column(db.Boolean, default=False)
    open_time = db.Column(db.String)
    close_time = db.Column(db.String)
    start_day = db.Column(db.String)

    def toDict(self):
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}


class User(db.Model):
    '''Users for authentication'''
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, server_default="TRUE", nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    roles = db.relationship('Role', secondary='user_roles')


class Role(db.Model):
    '''User Roles'''
    __tablename__ = 'roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True)


class UserRoles(db.Model):
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('roles.id', ondelete='CASCADE'))
