from flask import current_app, g, request
from ..http import body, owner, protected, respond
from backend.application import review_promotion_service
from backend.application import order_service
from backend.application import payment_service
from flask import Blueprint
bp = Blueprint('order_controller', __name__)


@bp.post('/api/checkout/quote')
def checkout_quote():
    return respond(review_promotion_service.checkout_quote(data=body(), owner=owner()))


@bp.post('/api/orders')
@protected()
def place_order():
    return respond(order_service.place_order(data=body(), user=g.user, owner=owner(), config=current_app.config, headers=request.headers))


@bp.get('/api/orders')
@protected()
def orders():
    return respond(order_service.orders(user=g.user))


@bp.get('/api/orders/<int:oid>')
@protected()
def get_order(oid):
    return respond(order_service.get_order(oid, user=g.user))


@bp.post('/api/orders/<int:oid>/cancel')
@protected()
def cancel_order(oid):
    return respond(order_service.cancel_order(oid, user=g.user))


@bp.post('/api/orders/<int:oid>/payment/retry')
@protected()
def retry_payment(oid):
    return respond(payment_service.retry_payment(oid, user=g.user, config=current_app.config))


@bp.post('/api/demo/payments/<int:oid>')
@protected()
def demo_payment(oid):
    return respond(payment_service.demo_payment(oid, data=body(), user=g.user, config=current_app.config))


@bp.get('/api/notifications')
@protected()
def notifications():
    return respond(order_service.notifications(user=g.user))


@bp.route('/api/support', methods=['GET', 'POST'])
@protected()
def support():
    if request.method=='GET':
        return respond(order_service.list_support(user=g.user))
    return respond(order_service.create_support(data=body(),user=g.user))
