from backend.shared.validation import identifier
from .payment_service import create_payment
from .order_records import history, order_detail, own_order, safe_order
from .audit_service import audit
from .catalog_service import product
from .inventory_service import release
from .inventory_service import reserve
from .checkout_service import quote
from backend.data_infrastructure.database.connection import get_db
from backend.data_infrastructure.database.connection import now
from backend.data_infrastructure.database.connection import one
from backend.data_infrastructure.database.connection import rows
from backend.shared.validation import integer
from backend.shared.validation import require
from backend.shared.validation import text
import hashlib
import json
import re


def place_order(*, data, user, owner, config, headers):
    d = data
    recipient = text(d.get('recipient'), 'Người nhận', 2, 100)
    phone = text(d.get('phone'), 'Điện thoại', 9, 15)
    require(re.fullmatch('\\+?[0-9]{9,14}', phone), 'Số điện thoại không hợp lệ.')
    address = text(d.get('address'), 'Địa chỉ', 10, 500)
    method = {'cod':'COD','demo':'ONLINE'}.get(d.get('payment_method'), d.get('payment_method'))
    require(method in ['COD', 'ONLINE'], 'Phương thức thanh toán không hợp lệ.')
    require(method != 'ONLINE' or config['DEMO_MODE'], 'Thanh toán mô phỏng đã tắt.', 403)
    require(not d.get('promo'), 'Mã giảm giá không được hỗ trợ.')
    expected = integer(d.get('expected_subtotal'), 'Tạm tính', 0)
    key = text(headers.get('Idempotency-Key'), 'Mã yêu cầu', 8, 100)
    digest = hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    db = get_db()
    db.execute('BEGIN IMMEDIATE')
    existing = one('SELECT * FROM orders WHERE user_id=? AND idem_key=?', (user['id'], key))
    if existing:
        require(existing['request_hash'] == digest, 'Mã yêu cầu đã dùng cho nội dung khác.', 409)
        db.commit()
        return order_detail(existing['id'])
    q = quote(owner)
    require(q['items'], 'Giỏ hàng đang trống.', 409)
    require(expected == q['subtotal'], 'Giá đã thay đổi. Xem lại giỏ hàng trước khi đặt.', 409)
    for line in q['items']:
        require(line['published'] and line['available'] >= line['quantity'], f"{line['name']}: không đủ tồn kho.", 409)
    status = 'confirmed' if method == 'COD' else 'pending'
    cur = db.execute('INSERT INTO orders(user_id,idem_key,request_hash,recipient,phone,address,subtotal,discount,shipping,total,promo,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) RETURNING id', (user['id'], key, digest, recipient, phone, address, q['subtotal'], 0, q['shipping'], q['total'], '', status, now()))
    oid = cur.fetchone()['id']
    for p in q['items']:
        db.execute('INSERT INTO order_items(order_id,product_id,name,selling_unit,snapshot_details,quantity,price) VALUES(?,?,?,?,?,?,?)', (oid, p['id'], p['name'], p['selling_unit'], json.dumps({'pack_quantity':p['pack_quantity'],'details':p['details']},ensure_ascii=False), p['quantity'], p['price']))
    reserve(oid, user['id'])
    create_payment(oid, method, q['total'])
    history(oid, status, user['id'])
    db.execute('DELETE FROM cart_items WHERE cart_id=(SELECT id FROM carts WHERE owner=?)', (owner,))
    db.commit()
    return (order_detail(oid), 201)


def orders(*, user):
    return [order_detail(o['id']) for o in rows('SELECT id FROM orders WHERE user_id=? ORDER BY created_at DESC,rowid DESC', (user['id'],))]


def get_order(oid, *, user):
    own_order(oid, user=user)
    return order_detail(oid)


def cancel_order(oid, *, user):
    db = get_db()
    db.execute('BEGIN IMMEDIATE')
    o = own_order(oid, user=user)
    p = one('SELECT * FROM payments WHERE order_id=?', (oid,))
    require(o['status'] in ['pending', 'confirmed', 'payment_failed'], 'Đơn đã được xử lý, hãy tạo yêu cầu hỗ trợ.', 409)
    require(p['status'] not in ['PAID'], 'Đơn đã thanh toán cần nhân viên xử lý hoàn tiền.', 409)
    if o['status'] != 'payment_failed':
        release(oid, user['id'])
    db.execute("UPDATE orders SET status='cancelled' WHERE id=?", (oid,))
    db.execute("UPDATE payments SET status='FAILED',failure_reason='Order cancelled' WHERE order_id=?", (oid,))
    history(oid, 'cancelled', user['id'])
    db.commit()
    return order_detail(oid)


def notifications(*, user):
    return rows('SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC,rowid DESC LIMIT 100', (user['id'],))


def list_support(*, user):
    return rows('SELECT * FROM service_cases WHERE user_id=? ORDER BY created_at DESC,rowid DESC', (user['id'],))


def create_support(*, data, user):
    d = data
    oid = d.get('order_id')
    if oid is not None:
        identifier(oid, 'Đơn hàng')
        require(one('SELECT id FROM orders WHERE id=? AND user_id=?', (oid, user['id'])), 'Không có đơn hàng.', 404)
    db = get_db()
    cid = db.execute('INSERT INTO service_cases(user_id,order_id,subject,message,created_at) VALUES(?,?,?,?,?) RETURNING id', (user['id'], oid, text(d.get('subject'), 'Chủ đề', 3, 120), text(d.get('message'), 'Nội dung', 5, 2000), now())).fetchone()['id']
    audit(user['id'], 'support.create', cid)
    db.commit()
    return (one('SELECT * FROM service_cases WHERE id=?', (cid,)), 201)


def resolve_case(cid, *, data, user):
    d = data
    require(d.get('status') in ['open', 'in_progress', 'closed'], 'Trạng thái không hợp lệ.')
    require(one('SELECT id FROM service_cases WHERE id=?', (cid,)), 'Không có yêu cầu hỗ trợ.', 404)
    reply = text(d.get('reply'), 'Phản hồi', 3, 2000)
    db = get_db()
    db.execute('UPDATE service_cases SET status=?,reply=? WHERE id=?', (d['status'], reply, cid))
    audit(user['id'], 'support.' + d['status'], cid)
    db.commit()
    return {'ok': True}


def exception(*, data, user):
    d = data
    oid = d.get('order_id')
    pid = d.get('product_id')
    if oid is not None:
        identifier(oid, 'Đơn hàng')
        require(one('SELECT id FROM orders WHERE id=?', (oid,)), 'Không có đơn hàng.', 404)
    if pid is not None:
        identifier(pid, 'Sản phẩm')
        require(one('SELECT id FROM products WHERE id=?', (pid,)), 'Không có sản phẩm.', 404)
    require(oid is not None or pid is not None, 'Cần chọn đơn hàng hoặc sản phẩm.')
    db = get_db()
    cid = db.execute("INSERT INTO service_cases(order_id,product_id,subject,message,reply,created_at) VALUES(?,?,'Ngoại lệ vận hành',?,?,?) RETURNING id", (oid, pid, text(d.get('reason'), 'Lý do', 3, 1000), text(d.get('follow_up'), 'Hướng xử lý', 3, 1000), now())).fetchone()['id']
    audit(user['id'], 'exception.create', cid)
    db.commit()
    return {'id': cid}


def overview(*, user):
    role = user['role']
    data = {}
    if role in ['admin', 'warehouse']:
        data.update(products=[product(p) for p in rows('SELECT * FROM products ORDER BY rowid')], movements=rows('SELECT * FROM inventory_movements ORDER BY created_at DESC,rowid DESC LIMIT 100'), supply=rows('SELECT * FROM replenishments ORDER BY created_at DESC,rowid DESC'))
    if role == 'admin':
        data.update(customers=rows("SELECT id,name,email,phone,active FROM users WHERE role='customer'"), audit=rows('SELECT * FROM audit ORDER BY created_at DESC,rowid DESC LIMIT 100'))
    if role in ['admin', 'sales', 'warehouse']:
        data['orders'] = [safe_order(o['id'], user=user) for o in rows('SELECT id FROM orders ORDER BY created_at DESC,rowid DESC LIMIT 100')]
    if role in ['admin', 'sales']:
        data['support'] = rows('SELECT * FROM service_cases ORDER BY created_at DESC,rowid DESC LIMIT 100')
    return data
