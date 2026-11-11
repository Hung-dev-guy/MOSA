import json
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from backend.data_infrastructure.database.connection import connect, get_db, init_db
from backend.data_infrastructure.database.migrations import _upgrade_v1, legacy_id
from backend.shared.product_types import PRODUCT_FIELDS
from conftest import call, sign_in
from test_design_alignment import make_legacy


def test_only_six_types_no_category_storage_or_crud(app, client):
    types = client.get('/api/product-types').json
    assert [t['id'] for t in types] == ['pen', 'notebook', 'bag', 'toy', 'book', 'electric_device']
    assert [t['name'] for t in types] == ['Bút', 'Sổ / vở', 'Túi', 'Đồ chơi', 'Sách', 'Thiết bị điện']
    assert [f['id'] for f in next(t for t in types if t['id']=='book')['fields']] == ['category', 'minimum_age', 'publisher']
    assert client.get('/api/categories').status_code == 404
    sign_in(client, 'admin')
    assert call(client, 'POST', '/staff/categories', {'name':'Unexpected'}).status_code in [404,405]
    assert call(client, 'PATCH', '/staff/categories/' + str(uuid4()), {'name':'Unexpected'}).status_code in [404,405]
    assert 'categories' not in client.get('/api/staff/overview').json
    with app.app_context():
        db = get_db()
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='categories'").fetchone()
        assert 'category_id' not in {r[1] for r in db.execute('PRAGMA table_info(products)')}
        assert db.execute('PRAGMA user_version').fetchone()[0] == 3
        assert not db.execute("SELECT 1 FROM products WHERE status='ACTIVE' AND product_type IS NULL").fetchone()


@pytest.mark.parametrize('kind', PRODUCT_FIELDS)
def test_type_filters_cover_all_six_specializations(app, client, kind):
    result = client.get('/api/products?product_type=' + kind).json
    assert result['total'] > 0
    assert all(p['product_type'] == kind for p in result['items'])
    assert all('category_id' not in p for p in result['items'])
    with app.app_context():
        record = get_db().execute('SELECT filter_type,filter_value FROM search_filter WHERE query_id=?', (result['query_id'],)).fetchone()
        assert tuple(record) == ('CATEGORY', kind)
    detail = client.get('/api/products/' + result['items'][0]['id']).json
    assert set(detail['details']) == set(PRODUCT_FIELDS[kind])
    assert client.get(detail['image']).status_code == 200


def test_invalid_and_legacy_type_filters_are_not_silently_ignored(client):
    assert client.get('/api/products?product_type=unknown').status_code == 400
    assert client.get('/api/products?category=' + str(uuid4())).status_code == 400
    sign_in(client, 'admin')
    p = client.get('/api/products?product_type=pen').json['items'][0]
    assert call(client, 'PATCH', '/staff/products/' + p['id'], {'category_id':str(uuid4())}).status_code == 400
    assert call(client, 'PATCH', '/staff/products/' + p['id'], {'product_type':None, 'published':True}).status_code == 400
    assert call(client, 'PATCH', '/staff/products/' + p['id'], {'product_type':[]}).status_code == 400


def test_subtype_change_removes_old_record_and_updates_filters(app, client):
    sign_in(client, 'admin')
    pid = legacy_id('products', 1)
    p = call(client, 'PATCH', '/staff/products/' + pid, {'product_type':'book','details':{'category':'Khoa học','publisher':'Kim Đồng','minimum_age':None}})
    assert p.status_code == 200, p.json
    assert p.json['details']['category'] == 'Khoa học'
    assert pid in [x['id'] for x in client.get('/api/products?product_type=book').json['items']]
    assert pid not in [x['id'] for x in client.get('/api/products?product_type=pen').json['items']]
    with app.app_context():
        assert not get_db().execute('SELECT 1 FROM pen WHERE product_id=?', (pid,)).fetchone()
        assert get_db().execute('SELECT 1 FROM book WHERE product_id=?', (pid,)).fetchone()


def make_v2(path):
    make_legacy(path)
    with connect(path) as db:
        _upgrade_v1(db, path, (Path(__file__).parents[1] / 'backend/data_infrastructure/database/schema_v2.sql').read_text())
        category_id, product_id = str(uuid4()), str(uuid4())
        db.execute('INSERT INTO categories(id,name) VALUES(?,?)', (category_id, 'Giấy in cũ'))
        db.execute("INSERT INTO products(id,category_id,name,description,brand,price,selling_unit,image,status,stock) VALUES(?,?,'Giấy in cũ','Description','Old brand',89000,'Ram','/assets/paper.png','ACTIVE',5)", (product_id,category_id))
        cid = db.execute('SELECT id FROM carts LIMIT 1').fetchone()[0]
        db.execute('INSERT INTO cart_items(cart_id,product_id,quantity,unit_price) VALUES(?,?,1,89000)', (cid,product_id))
        db.commit()
    return category_id, product_id


def test_v2_migration_preserves_unknown_products_cart_and_category_archive(tmp_path):
    path = tmp_path / 'v2.sqlite'
    category_id, pid = make_v2(path)
    init_db(path, demo=False)
    with connect(path) as db:
        p = db.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
        assert p['name'] == 'Giấy in cũ' and p['stock'] == 5
        assert p['product_type'] is None and p['status'] == 'ARCHIVED'
        assert db.execute('SELECT quantity FROM cart_items WHERE product_id=?', (pid,)).fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 1
        archive = json.loads(db.execute("SELECT data FROM migration_archive WHERE name='v2.product_categories'").fetchone()[0])
        assert next(x for x in archive if x['id']==pid)['category_id'] == category_id
        assert next(x for x in archive if x['id']==pid)['status'] == 'ACTIVE'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE products SET status='ACTIVE' WHERE id=?", (pid,))
    with sqlite3.connect(str(path)+'.pre-design-v3.sqlite') as original:
        assert original.execute('SELECT category_id FROM products WHERE id=?', (pid,)).fetchone()[0] == category_id
    init_db(path, demo=False)
    with connect(path) as db:
        assert db.execute('SELECT COUNT(*) FROM products').fetchone()[0] == 2


def test_v2_migration_rolls_back_and_keeps_backup_on_failure(tmp_path):
    path = tmp_path / 'invalid-v2.sqlite'
    make_v2(path)
    with sqlite3.connect(path) as db:
        db.execute('UPDATE products SET category_id=?', (str(uuid4()),))
    with pytest.raises(RuntimeError, match='foreign key'):
        init_db(path, demo=False)
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 2
        assert 'category_id' in {r[1] for r in db.execute('PRAGMA table_info(products)')}
    assert Path(str(path)+'.pre-design-v3.sqlite').is_file()


def test_v2_migration_transaction_rolls_back_schema_changes(tmp_path):
    from backend.data_infrastructure.database.migrations import _upgrade_v2
    path = tmp_path / 'transaction.sqlite'
    make_v2(path)
    schema = (Path(__file__).parents[1] / 'backend/data_infrastructure/database/schema.sql').read_text()
    with connect(path) as db:
        with pytest.raises(sqlite3.OperationalError):
            _upgrade_v2(db, path, schema + 'THIS IS INVALID;\n')
        assert db.execute('PRAGMA user_version').fetchone()[0] == 2
        assert 'category_id' in {r[1] for r in db.execute('PRAGMA table_info(products)')}
        assert db.execute('SELECT COUNT(*) FROM categories').fetchone()[0] == 2
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='migration_archive'").fetchone()
        assert db.execute('PRAGMA foreign_keys').fetchone()[0] == 1


def test_newer_database_is_not_downgraded(tmp_path):
    path = tmp_path / 'future.sqlite'
    init_db(path, demo=False)
    with connect(path) as db:
        db.execute('PRAGMA user_version=99')
    with pytest.raises(RuntimeError, match='newer'):
        init_db(path, demo=False)
    with connect(path) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 99
