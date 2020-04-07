from flask import Blueprint

api = Blueprint('api', __name__)

from . import views  # noqa: F401
from . import public_views  # noqa: F401
