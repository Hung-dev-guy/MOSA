from conftest import call,sign_in
from test_orders import checkout
from backend.data_infrastructure.database.connection import get_db


def test_roles_and_block_existing_session(app,client):
    assert client.get('/api/staff/overview').status_code==401
    sign_in(client)
    assert client.get('/api/staff/overview').status_code==403
    admin=app.test_client()
    sign_in(admin,'admin')
    assert call(admin,'PATCH','/staff/customers/1',{'active':False}).status_code==200
    assert client.get('/api/orders').status_code==401
    assert call(admin,'PATCH','/staff/customers/2',{'active':False}).status_code==404
    assert call(admin,'PATCH','/staff/customers/1',{'active':'false'}).status_code==400


def test_catalogue_validation_archive_category_cycle(app,client):
    sign_in(client,'admin')
    assert call(client,'POST','/staff/products',{'name':'bad'}).status_code==400
    p=client.get('/api/products/1').json
    p.update(name='Bút mới',price=15000,published=True)
    r=call(client,'POST','/staff/products',p)
    assert r.status_code==200,r.json
    pid=r.json['id']
    assert client.get(f'/api/products/{pid}').status_code==200
    assert call(client,'PATCH',f'/staff/products/{pid}',{'published':False}).status_code==200
    assert client.get(f'/api/products/{pid}').status_code==404
    assert call(client,'PATCH','/staff/products/1',{'image':'/assets/../../backend/app.py'}).status_code==400
    assert call(client,'PATCH','/staff/categories/1',{'name':'Bút','parent_id':1}).status_code==400
    new=call(client,'POST','/staff/categories',{'name':'Bút con','parent_id':1}).json
    assert call(client,'PATCH','/staff/categories/1',{'name':'Bút','parent_id':new['id']}).status_code==400


def test_promotion_dates_minimum_and_bounds(client):
    call(client,'POST','/cart/items',{'product_id':3,'quantity':1})
    q=call(client,'POST','/checkout/quote',{'promo':'MOSA10'}).json
    assert q['discount']==8900 and q['total']==105100
    assert call(client,'POST','/checkout/quote',{'promo':'NOPE'}).status_code==409
    sign_in(client,'admin')
    d={'code':'EXPIRED','percent':10,'minimum':0,'starts_at':'2020-01-01T00:00:00Z','ends_at':'2021-01-01T00:00:00Z','active':True}
    assert call(client,'POST','/staff/promotions',d).status_code==200
    assert call(client,'POST','/checkout/quote',{'promo':'EXPIRED'}).status_code==409
    assert call(client,'POST','/staff/promotions',{**d,'code':'TOOBIG','percent':99}).status_code==400
    assert call(client,'PATCH','/staff/promotions/1',{'active':False}).status_code==200
    assert call(client,'POST','/checkout/quote',{'promo':'MOSA10'}).status_code==409


def test_inventory_supply_and_role_privacy(app,client):
    checkout(client,'cod',quantity=3)
    warehouse=app.test_client()
    sign_in(warehouse,'warehouse')
    assert call(warehouse,'POST','/staff/inventory',{'product_id':1,'quantity':-90,'kind':'adjustment','reason':'Correction'}).status_code==409
    r=call(warehouse,'POST','/staff/inventory',{'product_id':1,'quantity':10,'kind':'receipt','reason':'New stock'})
    assert r.json['stock']==100
    req=call(warehouse,'POST','/staff/supply',{'supplier':'Thiên Long','product_id':1,'quantity':20}).json
    assert call(warehouse,'POST',f'/staff/supply/{req["id"]}/receive',{}).status_code==200
    assert call(warehouse,'POST',f'/staff/supply/{req["id"]}/receive',{}).status_code==409
    data=warehouse.get('/api/staff/overview').json
    assert data['products'][0]['stock']==120
    assert 'customers' not in data and 'phone' not in data['orders'][0]
    assert call(warehouse,'PATCH','/staff/products/1',{'price':1}).status_code==403


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
        p=get_db().execute('SELECT stock,reserved FROM products WHERE id=1').fetchone()
        assert tuple(p)==(87,0)
    assert call(staff,'POST',f'/staff/orders/{oid}/shipment',{'provider':'Nhập tay demo','tracking_code':'DEMO-001'}).status_code==200
    event={'event_id':'tracking-event-001','status':'delivered','message':'Đã giao demo'}
    r=call(staff,'POST',f'/staff/orders/{oid}/tracking',event)
    assert r.json['status']=='delivered' and r.json['payment']['status']=='collected'
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
