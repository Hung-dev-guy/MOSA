from ..http import respond
from backend.application import catalogue_service
from flask import Blueprint
bp = Blueprint('product_controller', __name__)


@bp.get('/api/categories')
def categories():
    return respond(catalogue_service.categories())


@bp.get('/api/products/<int:pid>')
def detail(pid):
    return respond(catalogue_service.detail(pid))
