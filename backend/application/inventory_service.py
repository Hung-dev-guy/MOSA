from .audit_service import audit
from .catalogue_service import product
from backend.data_infrastructure.database.connection import get_db
from backend.data_infrastructure.database.connection import now
from backend.data_infrastructure.database.connection import one
from backend.data_infrastructure.database.connection import rows
from backend.shared.validation import integer
from backend.shared.validation import require
from backend.shared.validation import text


def movement(pid, quantity, kind, actor, order_id=None, reason=''):
    get_db().execute('INSERT INTO inventory_movements(product_id,order_id,quantity,kind,reason,actor,created_at) VALUES(?,?,?,?,?,?,?)', (pid, order_id, quantity, kind, reason, str(actor), now()))


def reserve(order_id, actor):
    db = get_db()
    for line in rows('SELECT * FROM order_items WHERE order_id=?', (order_id,)):
        p = one('SELECT * FROM products WHERE id=?', (line['product_id'],))
        require(p and p['published'] and (p['stock'] - p['reserved'] >= line['quantity']), f"{line['name']}: không đủ tồn kho.", 409)
        db.execute('UPDATE products SET reserved=reserved+? WHERE id=?', (line['quantity'], p['id']))
        movement(p['id'], line['quantity'], 'reserve', actor, order_id)


def release(order_id, actor):
    db = get_db()
    for line in rows('SELECT * FROM order_items WHERE order_id=?', (order_id,)):
        db.execute('UPDATE products SET reserved=reserved-? WHERE id=?', (line['quantity'], line['product_id']))
        movement(line['product_id'], -line['quantity'], 'release', actor, order_id)


def inventory(*, data, user):
    d = data
    pid = integer(d.get('product_id'), 'Sản phẩm')
    kind = d.get('kind')
    require(kind in ['receipt', 'adjustment'], 'Loại biến động không hợp lệ.')
    qty = integer(d.get('quantity'), 'Số lượng', -100000, 100000)
    require(qty != 0 and (kind != 'receipt' or qty > 0), 'Nhập kho phải có số lượng dương.')
    reason = text(d.get('reason'), 'Lý do', 3, 500)
    db = get_db()
    db.execute('BEGIN IMMEDIATE')
    p = one('SELECT * FROM products WHERE id=?', (pid,))
    require(p, 'Không có sản phẩm.', 404)
    require(p['stock'] + qty >= p['reserved'], 'Tồn kho mới nhỏ hơn lượng đã giữ cho đơn.', 409)
    db.execute('UPDATE products SET stock=stock+? WHERE id=?', (qty, pid))
    movement(pid, qty, kind, user['id'], reason=reason)
    audit(user['id'], 'inventory.' + kind, pid)
    db.commit()
    return product(one('SELECT * FROM products WHERE id=?', (pid,)))


def supply(*, data, user):
    d = data
    pid = integer(d.get('product_id'), 'Sản phẩm')
    require(one('SELECT id FROM products WHERE id=?', (pid,)), 'Không có sản phẩm.', 404)
    db = get_db()
    rid = db.execute('INSERT INTO replenishments(supplier,product_id,quantity,created_at) VALUES(?,?,?,?)', (text(d.get('supplier'), 'Nhà cung cấp', 2, 100), pid, integer(d.get('quantity'), 'Số lượng', 1, 100000), now())).lastrowid
    audit(user['id'], 'supply.request', rid)
    db.commit()
    return one('SELECT * FROM replenishments WHERE id=?', (rid,))


def receive(rid, *, user):
    db = get_db()
    db.execute('BEGIN IMMEDIATE')
    r = one('SELECT * FROM replenishments WHERE id=?', (rid,))
    require(r, 'Không có yêu cầu nhập hàng.', 404)
    require(r['status'] == 'requested', 'Đã nhận hàng cho yêu cầu này.', 409)
    db.execute('UPDATE products SET stock=stock+? WHERE id=?', (r['quantity'], r['product_id']))
    db.execute("UPDATE replenishments SET status='received' WHERE id=?", (rid,))
    movement(r['product_id'], r['quantity'], 'receipt', user['id'], reason='Replenishment ' + str(rid))
    audit(user['id'], 'supply.receive', rid)
    db.commit()
    return {'ok': True}
