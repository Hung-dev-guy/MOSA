from .catalog_service import product
from backend.data_infrastructure.database.connection import get_db, one, rows
from backend.shared.validation import identifier, integer, require


def ensure_cart(owner):
    customer = owner[2:] if owner.startswith('u:') else None
    get_db().execute('INSERT INTO carts(owner,customer_id) VALUES(?,?) ON CONFLICT DO NOTHING', (owner, customer))
    return one('SELECT * FROM carts WHERE owner=?', (owner,))


def cart(owner):
    record = ensure_cart(owner)
    items = [product(p) for p in rows('SELECT p.*,c.id AS cart_item_id,c.quantity,c.unit_price FROM cart_items c JOIN products p ON p.id=c.product_id WHERE cart_id=? ORDER BY c.created_at,c.rowid', (record['id'],))]
    return {**record, 'items': items, 'subtotal': sum(p['price'] * p['quantity'] for p in items)}


def merge_guest_cart(guest_owner, customer_id):
    target = ensure_cart('u:' + customer_id)
    guest = one('SELECT id FROM carts WHERE owner=?', (guest_owner,))
    if guest:
        for line in rows('SELECT * FROM cart_items WHERE cart_id=?', (guest['id'],)):
            get_db().execute('INSERT INTO cart_items(cart_id,product_id,quantity,unit_price) VALUES(?,?,?,?) ON CONFLICT(cart_id,product_id) DO UPDATE SET quantity=CASE WHEN cart_items.quantity+excluded.quantity>999 THEN 999 ELSE cart_items.quantity+excluded.quantity END', (target['id'], line['product_id'], line['quantity'], line['unit_price']))
        get_db().execute('DELETE FROM cart_items WHERE cart_id=?', (guest['id'],))


def view_cart(*, owner):
    result = cart(owner)
    get_db().commit()
    return result


def add_cart(*, data, owner):
    pid = identifier(data.get('product_id'), 'Sản phẩm')
    quantity = integer(data.get('quantity'), 'Số lượng', 1, 999)
    p = one("SELECT * FROM products WHERE id=? AND status='ACTIVE'", (pid,))
    require(p, 'Sản phẩm không còn được bán.', 404)
    db = get_db()
    record = ensure_cart(owner)
    existing = one('SELECT quantity FROM cart_items WHERE cart_id=? AND product_id=?', (record['id'], pid))
    require(quantity + (existing['quantity'] if existing else 0) <= 999, 'Tối đa 999 đơn vị mỗi sản phẩm.')
    db.execute('INSERT INTO cart_items(cart_id,product_id,quantity,unit_price) VALUES(?,?,?,?) ON CONFLICT(cart_id,product_id) DO UPDATE SET quantity=cart_items.quantity+excluded.quantity,unit_price=excluded.unit_price', (record['id'], pid, quantity, p['price']))
    result = cart(owner)
    db.commit()
    return result


def update_cart(pid, *, data, owner):
    record = ensure_cart(owner)
    require(one('SELECT 1 FROM cart_items WHERE cart_id=? AND product_id=?', (record['id'], pid)), 'Không có sản phẩm này trong giỏ.', 404)
    quantity = integer(data.get('quantity'), 'Số lượng', 1, 999)
    get_db().execute('UPDATE cart_items SET quantity=? WHERE cart_id=? AND product_id=?', (quantity, record['id'], pid))
    result = cart(owner)
    get_db().commit()
    return result


def remove_cart(pid, *, owner):
    record = ensure_cart(owner)
    require(one('SELECT 1 FROM cart_items WHERE cart_id=? AND product_id=?', (record['id'], pid)), 'Không có sản phẩm này trong giỏ.', 404)
    get_db().execute('DELETE FROM cart_items WHERE cart_id=? AND product_id=?', (record['id'], pid))
    result = cart(owner)
    get_db().commit()
    return result
