from concurrent.futures import ThreadPoolExecutor
from conftest import call,sign_in
from backend.data_infrastructure.database.connection import get_db


def checkout(c,method='demo',key='checkout-test-0001',quantity=2):
    sign_in(c)
    call(c,'POST','/cart/items',{'product_id':'6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086','quantity':quantity})
    subtotal=c.get('/api/cart').json['subtotal']
    return call(c,'POST','/orders',payload(subtotal,method),headers={'Idempotency-Key':key})


def payload(subtotal,method='demo'):
    return {'recipient':'Nguyễn An','phone':'0901234567','address':'12 Nguyễn Trãi, Hà Nội','payment_method':method,'expected_subtotal':subtotal}


def test_order_before_payment_idempotency_snapshot(app,client):
    r=checkout(client)
    assert r.status_code==201,r.json
    o=r.json
    assert o['discount']==0 and o['promo']==''
    assert o['total']==o['subtotal']+o['shipping']==o['payment']['amount']
    assert o['status']=='pending' and o['payment']['status']=='PENDING'
    assert call(client,'POST','/orders',payload(24000),headers={'Idempotency-Key':'checkout-test-0001'}).json['id']==o['id']
    assert call(client,'POST','/orders',payload(12000),headers={'Idempotency-Key':'checkout-test-0001'}).status_code==409
    with app.app_context():
        p=get_db().execute("SELECT * FROM products WHERE id='6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086'").fetchone()
        assert p['stock']==90 and get_db().execute('SELECT SUM(quantity) FROM inventory_reservations').fetchone()[0]==2
        get_db().execute("UPDATE products SET price=19000,name=? WHERE id='6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086'",('New Name',))
        get_db().commit()
    detail=client.get(f'/api/orders/{o["id"]}').json
    assert detail['items'][0]['price']==12000
    assert detail['items'][0]['name']!='New Name'
    assert client.get('/api/notifications').json


def test_payment_failed_retry_success_dedup(app,client):
    oid=checkout(client).json['id']
    d={'result':'failed','event_id':'event-failed-1'}
    assert call(client,'POST',f'/demo/payments/{oid}',d).json['status']=='payment_failed'
    assert call(client,'POST',f'/demo/payments/{oid}',d).status_code==200
    with app.app_context():
        assert get_db().execute("SELECT COALESCE(SUM(quantity),0) FROM inventory_reservations WHERE product_id='6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086'").fetchone()[0]==0
    assert call(client,'POST',f'/orders/{oid}/payment/retry',{}).json['id']==oid
    success={'result':'success','event_id':'event-success-1'}
    assert call(client,'POST',f'/demo/payments/{oid}',success).json['payment']['status']=='PAID'
    assert call(client,'POST',f'/demo/payments/{oid}',success).status_code==200
    assert call(client,'POST',f'/demo/payments/{oid}',{'result':'failed','event_id':'different-event'}).status_code==409
    assert call(client,'POST',f'/orders/{oid}/cancel',{}).status_code==409


def test_stock_price_rollback_and_auth(app,client):
    assert call(client,'POST','/orders',payload(0),headers={'Idempotency-Key':'checkout-stock-1'}).status_code==401
    sign_in(client)
    call(client,'POST','/cart/items',{'product_id':'6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086','quantity':91})
    assert call(client,'POST','/orders',payload(91*12000),headers={'Idempotency-Key':'checkout-stock-2'}).status_code==409
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM orders').fetchone()[0]==0
        assert get_db().execute('SELECT COALESCE(SUM(quantity),0) FROM inventory_reservations').fetchone()[0]==0
    call(client,'PATCH','/cart/items/6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086',{'quantity':1})
    assert call(client,'POST','/orders',payload(9000),headers={'Idempotency-Key':'checkout-stock-3'}).status_code==409
    assert client.get('/api/cart').json['items']


def test_private_orders_cancellation(app,client):
    o=checkout(client,'cod').json
    other=app.test_client()
    call(other,'POST','/auth/register',{'name':'Other User','email':'other@example.com','password':'Password12345'})
    assert other.get(f'/api/orders/{o["id"]}').status_code==404
    assert call(other,'POST',f'/orders/{o["id"]}/cancel',{}).status_code==404
    assert call(client,'POST',f'/orders/{o["id"]}/cancel',{}).json['status']=='cancelled'
    assert call(client,'POST',f'/orders/{o["id"]}/cancel',{}).status_code==409
    with app.app_context():
        assert get_db().execute("SELECT COALESCE(SUM(quantity),0) FROM inventory_reservations WHERE product_id='6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086'").fetchone()[0]==0


def test_concurrent_checkout_no_oversell(app):
    clients=[app.test_client(),app.test_client()]
    for i,c in enumerate(clients):
        call(c,'POST','/auth/register',{'name':f'Customer {i}','email':f'customer{i}@example.com','password':'Password12345'})
        call(c,'POST','/cart/items',{'product_id':'6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086','quantity':60})
    def place(i):
        return call(clients[i],'POST','/orders',payload(720000),headers={'Idempotency-Key':f'concurrent-key-{i}'}).status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(place,[0,1]))==[201,409]
    with app.app_context():
        assert get_db().execute("SELECT COALESCE(SUM(quantity),0) FROM inventory_reservations WHERE product_id='6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086'").fetchone()[0]==60


def test_pending_and_demo_off(app,client):
    oid=checkout(client).json['id']
    assert call(client,'POST',f'/demo/payments/{oid}',{'result':'pending','event_id':'pending-event-123'}).json['status']=='pending'
    app.config['DEMO_MODE']=False
    assert call(client,'POST',f'/demo/payments/{oid}',{'result':'success','event_id':'success-event-123'}).status_code==404


def test_order_rejects_discount_code_without_changing_cart(client):
    sign_in(client)
    call(client,'POST','/cart/items',{'product_id':'78cde59a-3138-587c-b5a2-be9ad8ee4389','quantity':4})
    q=call(client,'POST','/checkout/quote',{}).json
    assert q['subtotal']==356000 and q['shipping']==0 and q['total']==356000
    r=call(client,'POST','/orders',{**payload(356000),'promo':'MOSA10'},headers={'Idempotency-Key':'removed-promotion-test'})
    assert r.status_code==400
    assert client.get('/api/orders').json==[]
    assert client.get('/api/cart').json['subtotal']==356000
