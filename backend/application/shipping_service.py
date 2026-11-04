from backend.data_infrastructure.adapters.shipping_provider_adapter import shipment_record
from .audit_service import audit
from .fulfillment_service import transition
from .order_records import order_detail
from backend.data_infrastructure.database.connection import get_db
from backend.data_infrastructure.database.connection import now
from backend.data_infrastructure.database.connection import one
from backend.shared.validation import require
from backend.shared.validation import text


def shipment(oid, *, data, user):
    d = data
    provider = text(d.get('provider'), 'Đơn vị vận chuyển', 2, 100)
    tracking = text(d.get('tracking_code'), 'Mã vận đơn', 3, 100)
    db = get_db()
    db.execute('BEGIN IMMEDIATE')
    o = order_detail(oid)
    require(o['status'] in ['shipped', 'delivered'], 'Đơn cần được xuất kho trước khi gắn vận đơn.', 409)
    require(not o['shipment'], 'Đơn đã có vận đơn.', 409)
    db.execute('INSERT INTO shipments VALUES(?,?,?,?,?)', shipment_record(oid, provider, tracking))
    audit(user['id'], 'shipment.create', oid)
    db.commit()
    return order_detail(oid)


def tracking(oid, *, data, user):
    d = data
    event = text(d.get('event_id'), 'Mã sự kiện', 8, 100)
    status = d.get('status')
    require(status in ['in_transit', 'delivered', 'exception'], 'Trạng thái vận chuyển không hợp lệ.')
    message = text(d.get('message'), 'Nội dung', 3, 500)
    db = get_db()
    db.execute('BEGIN IMMEDIATE')
    s = one('SELECT * FROM shipments WHERE order_id=?', (oid,))
    require(s, 'Chưa có vận đơn.', 409)
    old = one('SELECT * FROM tracking_events WHERE event_id=?', (event,))
    if old:
        require(old['order_id'] == oid and old['status'] == status and (old['message'] == message), 'Sự kiện xung đột.', 409)
        db.commit()
        return order_detail(oid)
    require(s['status'] != 'delivered', 'Giao hàng đã hoàn thành.', 409)
    if status == 'delivered':
        o = order_detail(oid)
        if o['status'] != 'delivered':
            transition(oid, 'delivered', user['id'])
    db.execute('INSERT INTO tracking_events VALUES(?,?,?,?,?)', (event, oid, status, message, now()))
    db.execute('UPDATE shipments SET status=?,updated_at=? WHERE order_id=?', (status, now(), oid))
    audit(user['id'], 'tracking.' + status, oid)
    db.commit()
    return order_detail(oid)
