from conftest import call,sign_in
from backend.data_infrastructure.database.connection import get_db


def test_guest_merge_separate_units_update_delete(app,client):
    for pid,qty in [(1,1),(1,2),(7,1)]:
        assert call(client,'POST','/cart/items',{'product_id':pid,'quantity':qty}).status_code==200
    c=client.get('/api/cart').json
    assert len(c['items'])==2 and c['items'][0]['quantity']==3
    with app.app_context():
        assert get_db().execute('SELECT SUM(reserved) FROM products').fetchone()[0]==0
    assert call(client,'PATCH','/cart/items/1',{'quantity':4}).json['items'][0]['quantity']==4
    assert len(call(client,'DELETE','/cart/items/7').json['items'])==1
    assert call(client,'DELETE','/cart/items/7').status_code==404


def test_login_merge_and_isolation(app,client):
    call(client,'POST','/cart/items',{'product_id':1,'quantity':2})
    sign_in(client)
    assert client.get('/api/cart').json['items'][0]['quantity']==2
    call(client,'POST','/auth/logout')
    assert client.get('/api/cart').json['items']==[]
    call(client,'POST','/cart/items',{'product_id':1,'quantity':3})
    sign_in(client)
    assert client.get('/api/cart').json['items'][0]['quantity']==5
    assert app.test_client().get('/api/cart').json['items']==[]


def test_invalid_cart_quantities(client):
    for quantity in [0,-1,1.5,True,'2',1000,None]:
        assert call(client,'POST','/cart/items',{'product_id':1,'quantity':quantity}).status_code==400
    assert call(client,'POST','/cart/items',{'product_id':999,'quantity':1}).status_code==404
