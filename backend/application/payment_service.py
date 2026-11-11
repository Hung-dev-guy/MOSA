from .inventory_service import release
from .inventory_service import reserve
from .order_records import history
from .order_records import order_detail
from .order_records import own_order
from backend.data_infrastructure.database.connection import get_db
from backend.data_infrastructure.database.connection import now
from backend.data_infrastructure.database.connection import one
from backend.shared.validation import require
from backend.shared.validation import text
from backend.data_infrastructure.adapters.payment_gateway_adapter import initial_payment


def create_payment(order_id,method,amount):
    # The order and reservation already exist in the caller's transaction.
    get_db().execute('INSERT INTO payments(order_id,method,status,reference,amount,idempotency_key) VALUES(?,?,?,?,?,?)',initial_payment(order_id,method,amount)+(order_id,))


def retry_payment(oid, *, user, config):
    db = get_db()
    db.execute('BEGIN IMMEDIATE')
    o = own_order(oid, user=user)
    p = one('SELECT * FROM payments WHERE order_id=?', (oid,))
    require(p['method'] == 'ONLINE' and config['DEMO_MODE'], 'Không hỗ trợ yêu cầu này.', 409)
    require(o['status'] in ['pending', 'payment_failed'], 'Đơn không thể thanh toán lại.', 409)
    if o['status'] == 'payment_failed':
        reserve(oid, user['id'])
    db.execute("UPDATE orders SET status='pending' WHERE id=?", (oid,))
    db.execute("UPDATE payments SET status='PENDING',failure_reason=NULL WHERE order_id=?", (oid,))
    history(oid, 'pending', user['id'])
    db.commit()
    return order_detail(oid)


def demo_payment(oid, *, data, user, config):
    require(config['DEMO_MODE'], 'Demo đã tắt.', 404)
    d = data
    result = d.get('result')
    require(result in ['success', 'failed', 'pending'], 'Kết quả không hợp lệ.')
    event = text(d.get('event_id'), 'Mã sự kiện', 8, 100)
    db = get_db()
    db.execute('BEGIN IMMEDIATE')
    own_order(oid, user=user)
    previous = one('SELECT * FROM payment_events WHERE event_id=?', (event,))
    if previous:
        require(previous['order_id'] == oid and previous['result'] == result, 'Mã sự kiện xung đột.', 409)
        db.commit()
        return order_detail(oid)
    p = one('SELECT * FROM payments WHERE order_id=?', (oid,))
    require(p['method'] == 'ONLINE', 'Đơn này không dùng thanh toán demo.', 409)
    require(p['status'] == 'PENDING', 'Kết quả cuối đã được ghi nhận; không thể ghi đè.', 409)
    db.execute('INSERT INTO payment_events VALUES(?,?,?,?)', (event, oid, result, now()))
    if result == 'failed':
        release(oid, user['id'])
    status = {'success': 'confirmed', 'failed': 'payment_failed', 'pending': 'pending'}[result]
    db.execute('UPDATE payments SET status=?,failure_reason=?,updated_at=? WHERE order_id=?', ({'success':'PAID','failed':'FAILED','pending':'PENDING'}[result], 'Demo payment failed' if result == 'failed' else None,now(),oid))
    db.execute('UPDATE orders SET status=? WHERE id=?', (status, oid))
    history(oid, status, 'demo:' + str(user['id']))
    db.commit()
    return order_detail(oid)
