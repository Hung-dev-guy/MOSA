from conftest import call,sign_in
from test_orders import checkout


def test_reviews_delivered_only_bounds_duplicate(app,client):
    oid=checkout(client,'cod').json['id']
    d={'rating':5,'comment':'Bút viết rất tốt'}
    assert call(client,'POST','/products/1/reviews',d).status_code==403
    admin=app.test_client()
    sign_in(admin,'admin')
    for status in ['picking','packed','shipped','delivered']:
        assert call(admin,'POST',f'/staff/orders/{oid}/status',{'status':status}).status_code==200
    assert call(client,'POST','/products/1/reviews',{**d,'rating':6}).status_code==400
    assert call(client,'POST','/products/1/reviews',d).status_code==201
    assert call(client,'POST','/products/1/reviews',d).status_code==409
    assert client.get('/api/products/1').json['reviews'][0]['rating']==5


def test_period_reports_paid_scope_and_csv(app,client):
    oid=checkout(client).json['id']
    manager=app.test_client()
    sign_in(manager,'manager')
    assert manager.get('/api/staff/reports').json['revenue']==0
    call(client,'POST',f'/demo/payments/{oid}',{'result':'success','event_id':'report-event-success'})
    r=manager.get('/api/staff/reports').json
    assert r['revenue']==49000 and r['order_count']==1 and r['paid_orders']==1
    assert r['inventory'][0]['available']==88
    assert manager.get('/api/staff/reports?from=2000-01-01&to=2000-01-02').json['revenue']==0
    assert manager.get('/api/staff/reports?from=bad').status_code==400
    assert manager.get('/api/staff/reports?from=2030-01-02&to=2020-01-01').status_code==400
    csv=manager.get('/api/staff/reports.csv')
    assert csv.status_code==200 and '49000' in csv.text and 'phone' not in csv.text
    assert manager.get('/api/staff/overview').json=={}
