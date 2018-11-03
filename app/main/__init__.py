from flask import Blueprint

main = Blueprint('main', __name__)

# import here to avoid circular dependencies
from . import views, errors

