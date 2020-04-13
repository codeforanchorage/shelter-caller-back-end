class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


class UnauthorizedUse(Exception):
    status_code = 401
    message = "Unauthorized"

    def __init__(self, message=None, status_code=None, payload=None):
        Exception.__init__(self)
        if status_code is not None:
            self.status_code = status_code
        if message is not None:
            self.message = message
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


class ServerError(Exception):
    status_code = 500
    message = "Server Error"

    def __init__(self, message=None, status_code=None, payload=None):
        Exception.__init__(self)
        if status_code is not None:
            self.status_code = status_code
        if message is not None:
            self.message = message
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv
