from conftest import call,sign_in
from backend.data_infrastructure.database.connection import get_db


def test_guest_merge_separate_units_update_delete(app,client):
    for pid,qty in [('6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086',1),('6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086',2),('2842bdf6-b98e-51fb-b5e9-3489b2f1722c',1)]:
        assert call(client,'POST','/cart/items',{'product_id':pid,'quantity':qty}).status_code==200
    c=client.get('/api/cart').json
    assert len(c['items'])==2 and c['items'][0]['quantity']==3
    with app.app_context():
        assert get_db().execute('SELECT COALESCE(SUM(quantity),0) FROM inventory_reservations').fetchone()[0]==0
    assert call(client,'PATCH','/cart/items/6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086',{'quantity':4}).json['items'][0]['quantity']==4
    assert len(call(client,'DELETE','/cart/items/2842bdf6-b98e-51fb-b5e9-3489b2f1722c').json['items'])==1
    assert call(client,'DELETE','/cart/items/2842bdf6-b98e-51fb-b5e9-3489b2f1722c').status_code==404


def test_login_merge_and_isolation(app,client):
    call(client,'POST','/cart/items',{'product_id':'6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086','quantity':2})
    sign_in(client)
    assert client.get('/api/cart').json['items'][0]['quantity']==2
    call(client,'POST','/auth/logout')
    assert client.get('/api/cart').json['items']==[]
    call(client,'POST','/cart/items',{'product_id':'6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086','quantity':3})
    sign_in(client)
    assert client.get('/api/cart').json['items'][0]['quantity']==5
    assert app.test_client().get('/api/cart').json['items']==[]


def test_invalid_cart_quantities(client):
    for quantity in [0,-1,1.5,True,'2',1000,None]:
        assert call(client,'POST','/cart/items',{'product_id':'6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086','quantity':quantity}).status_code==400
    assert call(client,'POST','/cart/items',{'product_id':'cd638b38-5069-5228-a823-bb5003e3010c','quantity':1}).status_code==404
