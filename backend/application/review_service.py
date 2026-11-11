from backend.data_infrastructure.database.connection import get_db, now, one
from backend.shared.validation import integer, require, text

def review(pid, *, data, user):
    d = data
    require(one("SELECT 1 FROM orders o JOIN order_items i ON i.order_id=o.id WHERE o.user_id=? AND i.product_id=? AND o.status='delivered'", (user['id'], pid)), 'Chỉ đánh giá sản phẩm trong đơn đã giao.', 403)
    rating = integer(d.get('rating'), 'Điểm đánh giá', 1, 5)
    comment = text(d.get('comment'), 'Đánh giá', 3, 1000)
    db = get_db()
    db.execute('INSERT INTO reviews(user_id,product_id,rating,comment,created_at) VALUES(?,?,?,?,?)', (user['id'], pid, rating, comment, now()))
    db.execute('UPDATE products SET average_rating=(SELECT AVG(rating) FROM reviews WHERE product_id=?),updated_at=? WHERE id=?', (pid,now(),pid))
    db.commit()
    return ({'ok': True}, 201)
