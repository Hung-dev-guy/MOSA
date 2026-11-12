from backend.shared.product_types import PRODUCT_FIELDS, product_types
from .audit_service import audit
from backend.data_infrastructure.database.connection import get_db, now
from backend.data_infrastructure.database.connection import one
from backend.data_infrastructure.database.connection import rows
from backend.data_infrastructure.storage.image_storage import validate_image_reference
from backend.shared.validation import boolean
from backend.shared.validation import integer
from backend.shared.validation import require
from backend.shared.validation import text
from backend.shared.validation import identifier
import json



def product(row):
    p = dict(row)
    p['attributes'] = json.loads(p['attributes'])
    p['pack_quantity'] = p['attributes'].get('pack_quantity', 1)
    p['published'] = p['status'] == 'ACTIVE'
    p['reserved'] = one('SELECT COALESCE(SUM(quantity),0) AS quantity FROM inventory_reservations WHERE product_id=?', (p['id'],))['quantity']
    p['available'] = p['stock'] - p['reserved']
    p['details'] = {}
    if p['product_type']:
        detail = one('SELECT * FROM ' + p['product_type'] + ' WHERE product_id=?', (p['id'],))
        p['details'] = {k:v for k,v in (detail or {}).items() if k != 'product_id'}
    return p


def published_products():
    return [product(p) for p in rows("SELECT * FROM products WHERE status='ACTIVE' ORDER BY rowid")]


def detail(pid):
    p = one("SELECT * FROM products WHERE id=? AND status='ACTIVE'", (pid,))
    require(p, 'Sản phẩm không còn được bán.', 404)
    return {**product(p), 'images': rows('SELECT * FROM product_image WHERE product_id=? ORDER BY is_primary DESC,created_at', (pid,)), 'reviews': rows('SELECT r.id,r.rating,r.comment,r.created_at,u.name FROM reviews r JOIN users u ON u.id=r.user_id WHERE product_id=? ORDER BY r.created_at DESC,r.rowid DESC', (pid,))}


def save_product(pid=None, *, data, user):
    old = one('SELECT * FROM products WHERE id=?', (pid,)) if pid else None
    require(not pid or old, 'Không tìm thấy sản phẩm.', 404)
    previous = product(old) if old else {}
    d = {**previous, **data}
    require('category_id' not in data, 'Danh mục cũ đã bỏ. Chọn product_type trong sáu loại sản phẩm.')
    attrs = d.get('attributes', {})
    require(isinstance(attrs, dict) and len(attrs) <= 20, 'Thông số cần là object tối đa 20 thuộc tính.')
    attrs = dict(attrs)
    for k,v in attrs.items():
        text(k, 'Tên thuộc tính', 1, 50)
        require(isinstance(v, (str,int)) and not isinstance(v,bool), 'Giá trị thông số cần là chuỗi hoặc số nguyên.')
        text(str(v), 'Giá trị thuộc tính', 1, 100)
    if 'pack_quantity' in data:
        attrs['pack_quantity'] = integer(data['pack_quantity'], 'Số lượng trong đơn vị', 1, 10000)
    for key in ['color','type','page_num','size','pattern','minimum_age','category','publisher','weight','màu','khổ','trang']:
        if d.get('product_type') and key in attrs:
            attrs.pop(key)
    image = text(d.get('image', '/assets/notebook.png'), 'Ảnh', 1, 2048)
    validate_image_reference(image)
    status = data.get('status', d.get('status', 'ARCHIVED'))
    if 'published' in data:
        status = 'ACTIVE' if boolean(data['published'], 'Xuất bản') else 'ARCHIVED'
    require(status in ['ACTIVE', 'ARCHIVED'], 'Trạng thái sản phẩm không hợp lệ.')
    kind = d.get('product_type')
    require((isinstance(kind, str) and kind in PRODUCT_FIELDS) or (old and kind is None and status == 'ARCHIVED'), 'Chọn một trong sáu loại sản phẩm.')
    details = {}
    if kind:
        incoming = data.get('details', previous.get('details', {}) if previous.get('product_type') == kind else {})
        require(isinstance(incoming, dict), 'Thông số loại sản phẩm cần là object.')
        require(not set(incoming) - set(PRODUCT_FIELDS[kind]), 'Thông số không thuộc loại sản phẩm đã chọn.')
        for field, required in PRODUCT_FIELDS[kind].items():
            value = incoming.get(field)
            if value is None or value == '':
                require(not required, 'Thiếu thông số: ' + field)
                details[field] = None
            elif field in ['page_num', 'minimum_age', 'weight']:
                details[field] = integer(value, field, 1 if field == 'page_num' else 0, 1000000)
            else:
                details[field] = text(value, field, 1, 150 if field == 'publisher' else 100 if field in ['category','pattern'] else 50)
    values = (text(d.get('name'), 'Tên sản phẩm', 2, 200), text(d.get('description',''), 'Mô tả', 0, 3000), text(d.get('brand',''), 'Thương hiệu', 0, 100), integer(d.get('price'), 'Giá', 1, 1000000000000), text(d.get('selling_unit'), 'Đơn vị bán', 1, 30), json.dumps(attrs, ensure_ascii=False), image, status, kind, text(d.get('origin') or '', 'Xuất xứ', 0, 100), text(d.get('material') or '', 'Chất liệu', 0, 100))
    db = get_db()
    if pid:
        db.execute('UPDATE products SET name=?,description=?,brand=?,price=?,selling_unit=?,attributes=?,image=?,status=?,product_type=?,origin=?,material=?,updated_at=? WHERE id=?', values + (now(),pid))
    else:
        pid = db.execute('INSERT INTO products(name,description,brand,price,selling_unit,attributes,image,status,product_type,origin,material) VALUES(?,?,?,?,?,?,?,?,?,?,?) RETURNING id', values).fetchone()['id']
    for table in PRODUCT_FIELDS:
        db.execute('DELETE FROM ' + table + ' WHERE product_id=?', (pid,))
    if kind:
        fields = ','.join(details)
        db.execute('INSERT INTO ' + kind + '(product_id,' + fields + ') VALUES(' + ','.join('?' for _ in range(len(details)+1)) + ')', (pid,*details.values()))
    db.execute('UPDATE product_image SET is_primary=0 WHERE product_id=?', (pid,))
    db.execute('INSERT INTO product_image(product_id,image_url,is_primary) VALUES(?,?,1) ON CONFLICT(product_id,image_url) DO UPDATE SET is_primary=1', (pid,image))
    audit(user['id'], 'catalogue.save', pid)
    db.commit()
    return product(one('SELECT * FROM products WHERE id=?', (pid,)))


def create_product(*, data, user):
    return save_product(data=data, user=user)


def edit_product(pid, *, data, user):
    return save_product(pid, data=data, user=user)


def delete_product(pid, *, user):
    identifier(pid, 'Sản phẩm')
    db = get_db()
    db.execute('BEGIN IMMEDIATE')
    require(one('SELECT id FROM products WHERE id=?', (pid,)), 'Không tìm thấy sản phẩm.', 404)
    # Preserve purchase, inventory, support and review history.
    for table in ('order_items', 'inventory_reservations', 'inventory_movements', 'replenishments', 'service_cases', 'reviews'):
        require(not one('SELECT 1 FROM ' + table + ' WHERE product_id=?', (pid,)),
                'Sản phẩm đã có đơn hàng hoặc lịch sử nghiệp vụ. Hãy bỏ chọn “Xuất bản trên cửa hàng” để ngừng bán.', 409)
    for table in ('cart_items', 'search_result', 'product_image', 'catalogue_sources', *PRODUCT_FIELDS):
        db.execute('DELETE FROM ' + table + ' WHERE product_id=?', (pid,))
    db.execute('DELETE FROM products WHERE id=?', (pid,))
    audit(user['id'], 'catalogue.delete', pid)
    db.commit()
    return {'ok': True, 'id': pid}

