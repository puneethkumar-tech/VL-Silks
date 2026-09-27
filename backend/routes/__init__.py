# VL Silks Routes Package
from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api')
web_bp = Blueprint('web', __name__)
