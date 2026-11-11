from .catalog_service import product
from backend.data_infrastructure.database.connection import now
from backend.data_infrastructure.database.connection import rows
from backend.shared.validation import require
from datetime import datetime
from datetime import timedelta
from datetime import timezone


def report(*, query):
    try:
        start = datetime.strptime(query.get('from', now()[:10]), '%Y-%m-%d').replace(tzinfo=timezone.utc)
        end = datetime.strptime(query.get('to', now()[:10]), '%Y-%m-%d').replace(tzinfo=timezone.utc) + timedelta(days=1)
    except ValueError:
        require(False, 'Ngày báo cáo cần dạng YYYY-MM-DD.')
    require(start < end, 'Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.')
    period = (start.isoformat(timespec='seconds'), end.isoformat(timespec='seconds'))
    orders = rows('SELECT o.*,p.status AS payment_status FROM orders o JOIN payments p ON p.order_id=o.id WHERE o.created_at>=? AND o.created_at<?', period)
    paid = [o for o in orders if o['payment_status'] in ['PAID']]
    counts = {}
    for o in orders:
        counts[o['status']] = counts.get(o['status'], 0) + 1
    return {'from': period[0], 'to_exclusive': period[1], 'generated_at': now(), 'revenue': sum((o['total'] for o in paid)), 'paid_orders': len(paid), 'order_count': len(orders), 'status_counts': counts, 'definition': 'Đơn tạo trong kỳ UTC; doanh thu gồm total của payment PAID tại thời điểm báo cáo. COD chưa thu không tính. Không có hoàn tiền tự động.', 'inventory': [{k:p[k] for k in ['id','name','stock','reserved','available']} for p in [product(row) for row in rows('SELECT * FROM products ORDER BY rowid')]], 'service': rows('SELECT status,COUNT(*) AS count FROM service_cases WHERE created_at>=? AND created_at<? GROUP BY status', period)}
