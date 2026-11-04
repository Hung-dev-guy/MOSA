from .audit_service import audit
from .cart_service import cart
from backend.data_infrastructure.database.connection import get_db
from backend.data_infrastructure.database.connection import now
from backend.data_infrastructure.database.connection import one
from backend.shared.validation import boolean
from backend.shared.validation import integer
from backend.shared.validation import require
from backend.shared.validation import text
from backend.shared.validation import timestamp


def quote(owner, code=''):
    c = cart(owner)
    discount = 0
    code = code.strip().upper()
    if code:
        p = one('SELECT * FROM promotions WHERE code=?', (code,))
        require(p and p['active'] and (p['starts_at'] <= now() <= p['ends_at']) and (c['subtotal'] >= p['minimum']), 'Mã giảm giá không hợp lệ, hết hạn hoặc chưa đủ điều kiện.', 409)
        discount = c['subtotal'] * p['percent'] // 100
    shipping = 0 if c['subtotal'] - discount >= 300000 else 25000
    return {**c, 'discount': discount, 'shipping': shipping, 'total': c['subtotal'] - discount + shipping, 'promo': code}


def checkout_quote(*, data, owner):
    return quote(owner, text(data.get('promo', ''), 'Mã giảm', 0, 40))


def save_promotion(pid=None, *, data, user):
    old = one('SELECT * FROM promotions WHERE id=?', (pid,)) if pid else None
    require(not pid or old, 'Không có ưu đãi này.', 404)
    incoming = data
    d = {**(old or {}), **incoming}
    code = text(d.get('code'), 'Mã ưu đãi', 2, 30).upper()
    require(code.isalnum(), 'Mã ưu đãi chỉ chứa chữ và số.')
    start = timestamp(d.get('starts_at'))
    end = timestamp(d.get('ends_at'))
    require(start < end, 'Ngày kết thúc phải sau ngày bắt đầu.')
    active = incoming.get('active', bool(old['active']) if old else True)
    values = (code, integer(d.get('percent'), 'Phần trăm', 1, 50), integer(d.get('minimum'), 'Giá trị tối thiểu', 0), start, end, boolean(active, 'Kích hoạt'))
    db = get_db()
    if pid:
        db.execute('UPDATE promotions SET code=?,percent=?,minimum=?,starts_at=?,ends_at=?,active=? WHERE id=?', values + (pid,))
    else:
        pid = db.execute('INSERT INTO promotions(code,percent,minimum,starts_at,ends_at,active) VALUES(?,?,?,?,?,?)', values).lastrowid
    audit(user['id'], 'promotion.save', pid)
    db.commit()
    return one('SELECT * FROM promotions WHERE id=?', (pid,))


def review(pid, *, data, user):
    d = data
    require(one("SELECT 1 FROM orders o JOIN order_items i ON i.order_id=o.id WHERE o.user_id=? AND i.product_id=? AND o.status='delivered'", (user['id'], pid)), 'Chỉ đánh giá sản phẩm trong đơn đã giao.', 403)
    rating = integer(d.get('rating'), 'Điểm đánh giá', 1, 5)
    comment = text(d.get('comment'), 'Đánh giá', 3, 1000)
    db = get_db()
    db.execute('INSERT INTO reviews(user_id,product_id,rating,comment,created_at) VALUES(?,?,?,?,?)', (user['id'], pid, rating, comment, now()))
    db.commit()
    return ({'ok': True}, 201)
