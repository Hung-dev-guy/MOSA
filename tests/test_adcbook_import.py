import copy
import sqlite3

import pytest

from backend.data_infrastructure.database.connection import get_db
from conftest import call, sign_in
from scripts.import_adcbook import normalized_product, apply_records, safe_url
from test_orders import payload


def source():
    return {'id':10, 'name':'Bút mẫu', 'product_type':'Bút gel (Nội bộ)',
            'url':'/but-mau', 'tags':['thuonghieu_Thiên Long','mausac_Xanh'],
            'featured_image':'https://bizweb.dktcdn.net/sample.png'}


def variant(vid=11):
    return {'id':vid, 'title':'Default Title', 'price':9000, 'unit':'Chiếc', 'available':False}


def record():
    item = normalized_product(source(), variant(), 'pen')
    item['image'] = '/assets/pen-blue.png'
    return item


def test_variants_and_required_source_facts():
    first = normalized_product(source(), variant(), 'pen')
    second_variant = {**variant(12), 'title':'Đỏ'}
    second = normalized_product(source(), second_variant, 'pen')
    assert first['id'] != second['id']
    assert second['name'].endswith(' — Đỏ')
    assert not first['source_available']
    assert first['details']['type'] == 'Bút gel'
    for kind in ['notebook','bag','book']:
        with pytest.raises(ValueError):
            normalized_product(source(), variant(), kind)
    notebook = {**source(), 'tags':['sotrang_240','kichthuoc_17 x 25 cm']}
    assert normalized_product(notebook, variant(), 'notebook')['details']['page_num'] == 240
    device = normalized_product(source(), {**variant(), 'unit':None}, 'electric_device')
    assert device['selling_unit'] == 'Chiếc' and device['source_selling_unit'] is None


@pytest.mark.parametrize('price', [0, -1, 'NaN', 'Infinity', '9000.5', 'invalid'])
def test_invalid_prices_rejected(price):
    with pytest.raises(ValueError):
        normalized_product(source(), {**variant(), 'price':price}, 'pen')


@pytest.mark.parametrize('url', ['http://adcbook.net.vn/a','https://example.org/a','https://user:pass@adcbook.net.vn/a'])
def test_source_url_boundary(url):
    with pytest.raises(ValueError):
        safe_url(url, image=True)


def test_import_is_atomic_and_idempotent(app):
    with app.app_context():
        db = get_db()
        item = record()
        apply_records(db, [item], 100)
        apply_records(db, [item], 100)
        assert db.execute('SELECT stock,status FROM products WHERE id=?',(item['id'],)).fetchone()[:] == (100,'ACTIVE')
        assert db.execute('SELECT COUNT(*) FROM pen WHERE product_id=?',(item['id'],)).fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM inventory_movements WHERE product_id=?',(item['id'],)).fetchone()[0] == 1
        assert db.execute('SELECT source_available,demo_available FROM catalogue_sources WHERE product_id=?',(item['id'],)).fetchone()[:] == (0,100)
        before = db.execute('SELECT COUNT(*) FROM products').fetchone()[0]
        valid = copy.deepcopy(item)
        valid['id'] = normalized_product(source(),variant(13),'pen')['id']
        invalid = copy.deepcopy(item)
        invalid['id'] = normalized_product(source(),variant(14),'pen')['id']
        invalid['details']['type'] = None
        with pytest.raises(sqlite3.IntegrityError):
            apply_records(db, [valid,invalid], 100)
        assert db.execute('SELECT COUNT(*) FROM products').fetchone()[0] == before
        assert not db.execute('PRAGMA foreign_key_check').fetchall()


def test_reimport_preserves_order_and_reserved_stock(app, client):
    item = record()
    with app.app_context():
        apply_records(get_db(), [item], 100)
    sign_in(client)
    assert call(client,'POST','/cart/items',{'product_id':item['id'],'quantity':3}).status_code == 200
    subtotal = client.get('/api/cart').json['subtotal']
    response = call(client,'POST','/orders',payload(subtotal),headers={'Idempotency-Key':'adcbook-reimport-01'})
    assert response.status_code == 201, response.json
    order_id = response.json['id']
    before = client.get('/api/orders/'+order_id).json
    with app.app_context():
        db = get_db()
        apply_records(db, [item], 100)
        assert db.execute('SELECT stock FROM products WHERE id=?',(item['id'],)).fetchone()[0] == 103
        assert db.execute('SELECT SUM(quantity) FROM inventory_reservations WHERE product_id=?',(item['id'],)).fetchone()[0] == 3
    assert client.get('/api/orders/'+order_id).json == before
