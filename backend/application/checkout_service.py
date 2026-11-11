from .cart_service import cart
from backend.data_infrastructure.database.connection import get_db
from backend.shared.validation import require


def quote(owner):
    c = cart(owner)
    shipping = 0 if c['subtotal'] >= 300000 else 25000
    return {**c, 'shipping': shipping, 'total': c['subtotal'] + shipping}


def checkout_quote(*, data, owner):
    require(not data.get('promo'), 'Mã giảm giá không được hỗ trợ.')
    result = quote(owner)
    get_db().commit()
    return result
