from flask import g
from ..http import body, protected, respond
from backend.application import review_service
from backend.application import catalog_service
from flask import Blueprint
bp = Blueprint('product_controller', __name__)


@bp.get('/api/product-types')
def product_types():
    return respond(catalog_service.product_types())


@bp.get('/api/products/<pid>')
def detail(pid):
    return respond(catalog_service.detail(pid))


@bp.post('/api/products/<pid>/reviews')
@protected()
def review(pid):
    return respond(review_service.review(pid, data=body(), user=g.user))
