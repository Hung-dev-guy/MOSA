from conftest import call,sign_in
from test_orders import checkout
from backend.data_infrastructure.database.connection import get_db


def test_roles_and_block_existing_session(app,client):
    assert client.get('/api/staff/overview').status_code==401
    sign_in(client)
    assert client.get('/api/staff/overview').status_code==403
    admin=app.test_client()
    sign_in(admin,'admin')
    assert call(admin,'PATCH','/staff/customers/345da7ed-77f1-56fd-91e0-2b8a55308efe',{'active':False}).status_code==200
    assert client.get('/api/orders').status_code==401
    assert call(admin,'PATCH','/staff/customers/ad2d928a-5525-5eb6-9f14-6edc3e755c4f',{'active':False}).status_code==404
    assert call(admin,'PATCH','/staff/customers/345da7ed-77f1-56fd-91e0-2b8a55308efe',{'active':'false'}).status_code==400


def test_catalogue_validation_and_archive(app,client):
    sign_in(client,'admin')
    assert call(client,'POST','/staff/products',{'name':'bad'}).status_code==400
    p=client.get('/api/products/6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086').json
    p.update(name='Bút mới',price=15000,published=True)
    r=call(client,'POST','/staff/products',p)
    assert r.status_code==200,r.json
    pid=r.json['id']
    assert client.get(f'/api/products/{pid}').status_code==200
    assert call(client,'PATCH',f'/staff/products/{pid}',{'published':False}).status_code==200
    assert client.get(f'/api/products/{pid}').status_code==404
    assert call(client,'PATCH','/staff/products/6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086',{'image':'/assets/../../backend/app.py'}).status_code==400


def test_discount_codes_are_not_supported(app,client):
    call(client,'POST','/cart/items',{'product_id':'78cde59a-3138-587c-b5a2-be9ad8ee4389','quantity':1})
    q=call(client,'POST','/checkout/quote',{}).json
    assert q['subtotal']==89000 and q['shipping']==25000 and q['total']==114000
    assert 'promo' not in q and 'discount' not in q
    assert call(client,'POST','/checkout/quote',{'promo':'MOSA10'}).status_code==400
    sign_in(client,'admin')
    assert 'promotions' not in client.get('/api/staff/overview').json
    assert 'promotions' not in client.get('/api/staff/reports').json
    assert not any('promotions' in rule.rule for rule in app.url_map.iter_rules())
    assert call(client,'POST','/staff/promotions',{}).status_code==405
    assert call(client,'PATCH','/staff/promotions/4d4bb9f6-5e6f-5b50-b8a4-f423bc9c7dfb',{}).status_code==405


def test_inventory_supply_and_role_privacy(app,client):
    checkout(client,'cod',quantity=3)
    warehouse=app.test_client()
    sign_in(warehouse,'warehouse')
    assert call(warehouse,'POST','/staff/inventory',{'product_id':'6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086','quantity':-90,'kind':'adjustment','reason':'Correction'}).status_code==409
    r=call(warehouse,'POST','/staff/inventory',{'product_id':'6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086','quantity':10,'kind':'receipt','reason':'New stock'})
    assert r.json['stock']==100
    req=call(warehouse,'POST','/staff/supply',{'supplier':'Thiên Long','product_id':'6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086','quantity':20}).json
    assert call(warehouse,'POST',f'/staff/supply/{req["id"]}/receive',{}).status_code==200
    assert call(warehouse,'POST',f'/staff/supply/{req["id"]}/receive',{}).status_code==409
    data=warehouse.get('/api/staff/overview').json
    assert data['products'][0]['stock']==120
    assert 'customers' not in data and 'phone' not in data['orders'][0]
    assert call(warehouse,'PATCH','/staff/products/6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086',{'price':1}).status_code==403


def test_fulfilment_dispatch_once_tracking_dedupe(app,client):
    oid=checkout(client,'cod',quantity=3).json['id']
    staff=app.test_client()
    sign_in(staff,'admin')
    assert call(staff,'POST',f'/staff/orders/{oid}/status',{'status':'shipped'}).status_code==409
    for status in ['picking','packed','shipped']:
        r=call(staff,'POST',f'/staff/orders/{oid}/status',{'status':status})
        assert r.status_code==200,r.json
    assert call(staff,'POST',f'/staff/orders/{oid}/status',{'status':'shipped'}).status_code==409
    with app.app_context():
        p=get_db().execute("SELECT stock,COALESCE((SELECT SUM(quantity) FROM inventory_reservations WHERE product_id=products.id),0) AS reserved FROM products WHERE id='6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086'").fetchone()
        assert tuple(p)==(87,0)
    assert call(staff,'POST',f'/staff/orders/{oid}/shipment',{'provider':'Nhập tay demo','tracking_code':'DEMO-001'}).status_code==200
    event={'event_id':'tracking-event-001','status':'delivered','message':'Đã giao demo'}
    r=call(staff,'POST',f'/staff/orders/{oid}/tracking',event)
    assert r.json['status']=='delivered' and r.json['payment']['status']=='PAID'
    assert call(staff,'POST',f'/staff/orders/{oid}/tracking',event).status_code==200
    assert len(client.get(f'/api/orders/{oid}').json['tracking'])==1


def test_support_exception_audit(app,client):
    oid=checkout(client,'cod').json['id']
    case=call(client,'POST','/support',{'order_id':oid,'subject':'Đổi địa chỉ','message':'Xin thay địa chỉ giao hàng'}).json
    sales=app.test_client()
    sign_in(sales,'sales')
    assert call(sales,'PATCH',f'/staff/support/{case["id"]}',{'status':'closed','reply':'Đã liên hệ xác nhận'}).status_code==200
    assert client.get('/api/support').json[0]['reply']=='Đã liên hệ xác nhận'
    assert call(sales,'POST','/staff/exceptions',{'order_id':oid,'reason':'Thiếu thông tin','follow_up':'Gọi khách xác nhận'}).status_code==200
    assert sales.get('/api/staff/reports').status_code==403
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM audit').fetchone()[0]>=3
