from conftest import call, sign_in
from test_orders import checkout
from backend.data_infrastructure.database.connection import get_db


def create_product(client):
    response = call(client, 'POST', '/staff/products', {
        'name': 'Bút xoá kiểm thử', 'brand': 'Mosa', 'product_type': 'pen',
        'details': {'type': 'Gel', 'color': 'xanh'}, 'price': 15000,
        'selling_unit': 'Cây', 'published': True, 'image': '/assets/pen-blue.png',
    })
    assert response.status_code == 200, response.json
    return response.json['id']


def test_admin_delete_cleans_cart_search_and_product_details(app, client):
    sign_in(client, 'admin')
    pid = create_product(client)
    assert call(client, 'POST', '/cart/items', {'product_id': pid, 'quantity': 2}).status_code == 200
    result = client.get('/api/products?q=xoá').json
    assert any(item['id'] == pid for item in result['items'])
    assert call(client, 'DELETE', '/staff/products/' + pid).status_code == 200
    assert client.get('/api/products/' + pid).status_code == 404
    cart = client.get('/api/cart').json
    assert cart['items'] == [] and cart['status'] == 'EMPTY' and cart['subtotal'] == 0
    assert all(p['id'] != pid for p in client.get('/api/staff/overview').json['products'])
    with app.app_context():
        db = get_db()
        for table in ('pen', 'product_image', 'search_result', 'cart_items'):
            assert db.execute('SELECT count(*) FROM ' + table + ' WHERE product_id=?', (pid,)).fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM audit WHERE action='catalogue.delete' AND record=?", (pid,)).fetchone()[0] == 1
    assert call(client, 'DELETE', '/staff/products/' + pid).status_code == 404


def test_product_delete_requires_admin_and_valid_id(app, client):
    pid = '6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086'
    assert call(client, 'DELETE', '/staff/products/' + pid).status_code == 401
    sign_in(client)
    assert call(client, 'DELETE', '/staff/products/' + pid).status_code == 403
    warehouse = app.test_client()
    sign_in(warehouse, 'warehouse')
    assert call(warehouse, 'DELETE', '/staff/products/' + pid).status_code == 403
    admin = app.test_client()
    sign_in(admin, 'admin')
    assert admin.delete('/api/staff/products/' + pid).status_code == 403
    assert call(admin, 'DELETE', '/staff/products/not-a-uuid').status_code == 400


def test_product_delete_preserves_order_and_reservation(app, client):
    order = checkout(client, 'cod').json
    admin = app.test_client()
    sign_in(admin, 'admin')
    pid = order['items'][0]['product_id']
    response = call(admin, 'DELETE', '/staff/products/' + pid)
    assert response.status_code == 409
    assert 'ngừng bán' in response.json['error']
    assert client.get('/api/orders/' + order['id']).json['items'] == order['items']
    assert client.get('/api/products/' + pid).status_code == 200
    with app.app_context():
        db = get_db()
        assert db.execute('SELECT quantity FROM inventory_reservations WHERE product_id=?', (pid,)).fetchone()[0] == 2
        assert db.execute('SELECT count(*) FROM pen WHERE product_id=?', (pid,)).fetchone()[0] == 1


def test_product_delete_preserves_inventory_history(app, client):
    sign_in(client, 'admin')
    pid = create_product(client)
    assert call(client, 'POST', '/staff/inventory', {'product_id': pid, 'kind': 'receipt', 'quantity': 3, 'reason': 'Nhập kho thử'}).status_code == 200
    assert call(client, 'DELETE', '/staff/products/' + pid).status_code == 409
    assert client.get('/api/products/' + pid).json['stock'] == 3
