from flask import request
from ..http import body, owner, respond
from backend.application import cart_service
from flask import Blueprint
bp = Blueprint('cart_controller', __name__)


@bp.get('/api/cart')
def view_cart():
    return respond(cart_service.view_cart(owner=owner()))


@bp.post('/api/cart/items')
def add_cart():
    return respond(cart_service.add_cart(data=body(), owner=owner()))


@bp.route('/api/cart/items/<pid>', methods=['PATCH', 'DELETE'])
def update_cart(pid):
    if request.method=='DELETE':
        return respond(cart_service.remove_cart(pid,owner=owner()))
    return respond(cart_service.update_cart(pid,data=body(),owner=owner()))
