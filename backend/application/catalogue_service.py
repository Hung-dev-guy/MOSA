from .audit_service import audit
from backend.data_infrastructure.database.connection import get_db
from backend.data_infrastructure.database.connection import one
from backend.data_infrastructure.database.connection import rows
from backend.data_infrastructure.storage.image_storage import validate_image_reference
from backend.shared.validation import boolean
from backend.shared.validation import integer
from backend.shared.validation import require
from backend.shared.validation import text
import json


def product(row):
    p = dict(row)
    p['attributes'] = json.loads(p['attributes'])
    p['available'] = p['stock'] - p['reserved']
    return p


def categories():
    return rows('SELECT * FROM categories ORDER BY id')


def published_products():
    return [product(p) for p in rows('SELECT * FROM products WHERE published=1 ORDER BY id')]


def detail(pid):
    p = one('SELECT * FROM products WHERE id=? AND published=1', (pid,))
    require(p, 'Sản phẩm không còn được bán.', 404)
    return {**product(p), 'reviews': rows('SELECT r.id,r.rating,r.comment,r.created_at,u.name FROM reviews r JOIN users u ON u.id=r.user_id WHERE product_id=? ORDER BY r.id DESC', (pid,))}


def save_product(pid=None, *, data, user):
    d = data
    old = one('SELECT * FROM products WHERE id=?', (pid,)) if pid else None
    require(not pid or old, 'Không tìm thấy sản phẩm.', 404)
    d = {**(product(old) if old else {}), **d}
    category = integer(d.get('category_id'), 'Danh mục')
    require(one('SELECT id FROM categories WHERE id=?', (category,)), 'Danh mục không tồn tại.')
    attrs = d.get('attributes', {})
    require(isinstance(attrs, dict) and len(attrs) <= 20, 'Thông số cần là object tối đa 20 thuộc tính.')
    for k, v in attrs.items():
        text(k, 'Tên thuộc tính', 1, 50)
        text(v, 'Giá trị thuộc tính', 1, 100)
    image = text(d.get('image', '/assets/notebook.png'), 'Ảnh', 1, 200)
    validate_image_reference(image)
    published = d.get('published', False)
    if old and 'published' not in data:
        published = bool(old['published'])
    values = (category, text(d.get('name'), 'Tên sản phẩm', 2, 180), text(d.get('description'), 'Mô tả', 10, 3000), text(d.get('brand'), 'Thương hiệu', 1, 100), integer(d.get('price'), 'Giá', 1, 100000000), text(d.get('selling_unit'), 'Đơn vị bán', 1, 30), integer(d.get('pack_quantity'), 'Số lượng trong đơn vị', 1, 10000), json.dumps(attrs, ensure_ascii=False), image, boolean(published, 'Xuất bản'))
    db = get_db()
    if pid:
        db.execute('UPDATE products SET category_id=?,name=?,description=?,brand=?,price=?,selling_unit=?,pack_quantity=?,attributes=?,image=?,published=? WHERE id=?', values + (pid,))
    else:
        pid = db.execute('INSERT INTO products(category_id,name,description,brand,price,selling_unit,pack_quantity,attributes,image,published) VALUES(?,?,?,?,?,?,?,?,?,?)', values).lastrowid
    audit(user['id'], 'catalogue.save', pid)
    db.commit()
    return product(one('SELECT * FROM products WHERE id=?', (pid,)))


def create_product(*, data, user):
    return save_product(data=data, user=user)


def edit_product(pid, *, data, user):
    return save_product(pid, data=data, user=user)


def save_category(cid=None, *, data, user):
    d = data
    if cid:
        require(one('SELECT id FROM categories WHERE id=?', (cid,)), 'Không có danh mục.', 404)
    name = text(d.get('name'), 'Danh mục', 2, 100)
    parent = d.get('parent_id')
    if parent is not None:
        integer(parent, 'Danh mục cha')
        node = one('SELECT * FROM categories WHERE id=?', (parent,))
        require(node, 'Danh mục cha không tồn tại.')
        while node:
            require(node['id'] != cid, 'Danh mục cha không được tạo vòng lặp.')
            node = one('SELECT * FROM categories WHERE id=?', (node['parent_id'],))
    db = get_db()
    if cid:
        db.execute('UPDATE categories SET name=?,parent_id=? WHERE id=?', (name, parent, cid))
    else:
        cid = db.execute('INSERT INTO categories(name,parent_id) VALUES(?,?)', (name, parent)).lastrowid
    audit(user['id'], 'category.save', cid)
    db.commit()
    return one('SELECT * FROM categories WHERE id=?', (cid,))
