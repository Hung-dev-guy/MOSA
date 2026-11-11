import json
import sqlite3
from pathlib import Path
from uuid import UUID

import pytest

from backend.data_infrastructure.database.connection import connect, get_db, init_db
from backend.data_infrastructure.database.migrations import legacy_id
from conftest import call, sign_in


DETAILS = {
    'pen': {'type': 'Gel', 'color': None},
    'notebook': {'page_num': 120, 'size': 'A5', 'type': 'Lò xo'},
    'bag': {'size': '30 x 40 cm', 'pattern': None},
    'toy': {'type': 'Xếp hình', 'minimum_age': 6},
    'book': {'category': 'Khoa học', 'publisher': 'Kim Đồng', 'minimum_age': None},
    'electric_device': {'weight': 300, 'minimum_age': None},
}


@pytest.mark.parametrize('kind', DETAILS)
def test_subtype_shared_identity_validation_and_filters(app, client, kind):
    sign_in(client, 'admin')
    payload = {'name': 'Sản phẩm ' + kind, 'product_type': kind,
               'details': DETAILS[kind], 'price': 5_000_000_000, 'selling_unit': 'Chiếc',
               'origin': 'Việt Nam', 'material': 'Vật liệu thử', 'published': True}
    result = call(client, 'POST', '/staff/products', payload)
    assert result.status_code == 200, result.json
    p = result.json
    assert str(UUID(p['id'])) == p['id']
    assert p['price'] == 5_000_000_000 and p['origin'] == 'Việt Nam'
    assert p['details'] == DETAILS[kind]
    with app.app_context():
        db = get_db()
        assert db.execute('SELECT product_id FROM ' + kind + ' WHERE product_id=?', (p['id'],)).fetchone()[0] == p['id']
        assert sum(db.execute('SELECT COUNT(*) FROM ' + t + ' WHERE product_id=?', (p['id'],)).fetchone()[0] for t in DETAILS) == 1
        assert db.execute('SELECT COUNT(*) FROM product_image WHERE product_id=? AND is_primary=1', (p['id'],)).fetchone()[0] == 1
    if kind == 'notebook':
        assert call(client, 'PATCH', '/staff/products/' + p['id'], {'details': {**DETAILS[kind], 'page_num': 0}}).status_code == 400
        assert call(client, 'PATCH', '/staff/products/' + p['id'], {'details': {**DETAILS[kind], 'type': None}}).status_code == 400
    if kind == 'book':
        assert any(x['id'] == p['id'] for x in client.get('/api/products?publisher=Kim+Đồng').json['items'])


def test_uuid_cart_status_and_snapshot_price(app, client):
    assert client.get('/api/cart').json['status'] == 'EMPTY'
    pid = legacy_id('products', 1)
    assert call(client, 'POST', '/cart/items', {'product_id': 1, 'quantity': 1}).status_code == 400
    cart = call(client, 'POST', '/cart/items', {'product_id': pid, 'quantity': 2}).json
    assert cart['status'] == 'HAS_ITEMS'
    assert str(UUID(cart['id'])) == cart['id']
    assert str(UUID(cart['items'][0]['cart_item_id'])) == cart['items'][0]['cart_item_id']
    assert cart['items'][0]['unit_price'] == 12000
    assert call(client, 'DELETE', '/cart/items/' + pid).json['status'] == 'EMPTY'
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM inventory_reservations').fetchone()[0] == 0


def test_search_persistence_anonymous_voice_image_and_hard_filters(app, client):
    result = client.get('/api/products?q=bút&modality=VOICE&color=xanh').json
    assert result['modality'] == 'VOICE'
    with app.app_context():
        db = get_db()
        record = db.execute('SELECT * FROM search_query WHERE query_id=?', (result['query_id'],)).fetchone()
        assert record['customer_id'] is None and record['guest_owner'].startswith('g:')
        assert db.execute('SELECT filter_type FROM search_filter WHERE query_id=?', (result['query_id'],)).fetchone()[0] == 'COLOR'
        assert db.execute('SELECT COUNT(*) FROM search_result WHERE query_id=?', (result['query_id'],)).fetchone()[0] == len(result['items'])
        assert not db.execute('SELECT 1 FROM search_filter WHERE was_relaxed=1').fetchone()
    user = sign_in(client)['user']
    result = client.get('/api/products?q=bút').json
    token = client.get('/api/session').json['csrf_token']
    image = Path(__file__).resolve().parents[1] / 'frontend/public/assets/pen-blue.png'
    with image.open('rb') as f:
        media_result = client.post('/api/search/image', data={'image': (f, 'pen.png')}, headers={'X-CSRF-Token': token})
    assert media_result.status_code == 200, media_result.json
    with app.app_context():
        db = get_db()
        assert db.execute('SELECT customer_id FROM search_query WHERE query_id=?', (result['query_id'],)).fetchone()[0] == user['id']
        media = db.execute('SELECT * FROM query_media WHERE query_id=?', (media_result.json['query_id'],)).fetchone()
        assert media['media_type'] == 'IMAGE' and Path(media['storage_reference']).is_file()
        assert client.get('/assets/' + Path(media['storage_reference']).name).status_code == 404


def test_session_revocation_without_customer_version(app, client):
    sign_in(client)
    second = app.test_client()
    sign_in(second)
    assert call(client, 'POST', '/account/password', {'current_password': 'Mosa@12345', 'password': 'DifferentPassword123'}).status_code == 200
    assert client.get('/api/session').json['user']
    assert second.get('/api/session').json['user'] is None
    admin = app.test_client()
    sign_in(admin, 'admin')
    uid = legacy_id('users', 1)
    assert call(admin, 'PATCH', '/staff/customers/' + uid, {'active': False}).status_code == 200
    assert call(admin, 'PATCH', '/staff/customers/' + uid, {'active': True}).status_code == 200
    assert client.get('/api/session').json['user'] is None
    with app.app_context():
        assert 'session_version' not in {r[1] for r in get_db().execute('PRAGMA table_info(users)')}


def make_legacy(path):
    db = sqlite3.connect(path)
    db.executescript((Path(__file__).with_name('fixtures') / 'schema_v1.sql').read_text())
    db.execute("INSERT INTO users(id,name,email,password) VALUES(1,'Old Customer','old@example.com','old-hash')")
    db.execute("INSERT INTO categories(id,name) VALUES(1,'Bút')")
    db.execute("INSERT INTO products(id,category_id,name,description,brand,price,selling_unit,pack_quantity,attributes,image,published,stock,reserved) VALUES(1,1,'Old Pen','Old description','Brand',12000,'Hộp',12,'{}','/assets/pen-box.png',1,10,2)")
    db.execute("INSERT INTO cart_items VALUES('u:1',1,3)")
    db.execute("INSERT INTO orders(id,user_id,idem_key,request_hash,recipient,phone,address,subtotal,discount,shipping,total,status,created_at) VALUES(1,1,'old-key','hash','Recipient','0901234567','Old address',24000,0,25000,49000,'pending','2026-11-01')")
    db.execute("INSERT INTO order_items(order_id,product_id,name,selling_unit,pack_quantity,quantity,price) VALUES(1,1,'Old Pen','Hộp',12,2,12000)")
    db.execute("INSERT INTO payments VALUES(1,'demo','pending','old-reference',49000)")
    db.execute("INSERT INTO reviews(user_id,product_id,rating,comment,created_at) VALUES(1,1,4,'Old review','2026-11-01')")
    db.commit()
    db.close()


def test_legacy_migration_preserves_data_and_backup(tmp_path):
    path = tmp_path / 'old.sqlite'
    make_legacy(path)
    init_db(path, demo=False)
    with connect(path) as db:
        uid, pid, oid = (legacy_id(t, 1) for t in ['users', 'products', 'orders'])
        assert db.execute('PRAGMA user_version').fetchone()[0] == 3
        assert db.execute('SELECT password FROM users WHERE id=?', (uid,)).fetchone()[0] == 'old-hash'
        assert db.execute('SELECT total FROM orders WHERE id=?', (oid,)).fetchone()[0] == 49000
        assert db.execute('SELECT quantity FROM inventory_reservations WHERE order_id=? AND product_id=?', (oid, pid)).fetchone()[0] == 2
        assert json.loads(db.execute('SELECT snapshot_details FROM order_items').fetchone()[0])['pack_quantity'] == 12
        assert db.execute('SELECT status,method FROM payments').fetchone()[:] == ('PENDING', 'ONLINE')
        assert db.execute('SELECT status FROM carts WHERE customer_id=?', (uid,)).fetchone()[0] == 'HAS_ITEMS'
        assert db.execute('SELECT average_rating FROM products').fetchone()[0] == 4
        assert json.loads(db.execute('SELECT attributes FROM products').fetchone()[0])['pack_quantity'] == 12
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
    with sqlite3.connect(str(path) + '.pre-design-v2.sqlite') as original:
        assert original.execute('SELECT reserved FROM products WHERE id=1').fetchone()[0] == 2
    init_db(path, demo=False)
    with connect(path) as db:
        assert db.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 1


def test_migration_rolls_back_invalid_legacy_data(tmp_path):
    path = tmp_path / 'bad.sqlite'
    make_legacy(path)
    with sqlite3.connect(path) as db:
        db.execute('UPDATE products SET category_id=999')
    with pytest.raises(RuntimeError, match='foreign key'):
        init_db(path, demo=False)
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 0
        assert db.execute('SELECT id,reserved FROM products').fetchone() == (1, 2)
