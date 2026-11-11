import io
from pathlib import Path
from conftest import call
from backend.data_infrastructure.database.connection import get_db


def test_public_catalogue_combined_filters(client):
    result=client.get('/api/products?q=but&brand=Thiên+Long&product_type=pen&attribute=màu:xanh&min_price=10000&max_price=15000').json
    assert [p['id'] for p in result['items']]==['6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086']
    assert client.get('/api/products?q=nonexistent').json['total']==0
    assert client.get('/api/products?page=2').json['page']==2
    prices=[p['price'] for p in client.get('/api/products?sort=price_asc').json['items']]
    assert prices==sorted(prices)
    assert client.get('/api/products?page=-1').status_code==400
    assert client.get('/api/products?min_price=oops').status_code==400
    assert client.get('/api/products?sort=unknown').status_code==400


def test_hidden_product_and_detail(app,client):
    with app.app_context():
        get_db().execute("UPDATE products SET status='ARCHIVED' WHERE id='6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086'")
        get_db().commit()
    assert client.get('/api/products/6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086').status_code==404
    assert not any(p['id']=='6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086' for p in client.get('/api/products?q=but').json['items'])
    p=client.get('/api/products/2842bdf6-b98e-51fb-b5e9-3489b2f1722c').json
    assert p['selling_unit']=='Hộp' and p['pack_quantity']==12


def test_image_rank_validation_and_no_business_changes(app,client):
    token=client.get('/api/session').json['csrf_token']
    path=Path(__file__).resolve().parents[1]/'frontend/public/assets/pen-blue.png'
    with path.open('rb') as f:
        r=client.post('/api/search/image',data={'image':(f,'pen.png')},headers={'X-CSRF-Token':token})
    assert r.status_code==200,r.json
    assert r.json['items'][0]['id']=='6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086'
    with path.open('rb') as f:
        filtered=client.post('/api/search/image?product_type=notebook',data={'image':(f,'pen.png')},headers={'X-CSRF-Token':token})
    assert all(p['product_type']=='notebook' for p in filtered.json['items'])
    r=client.post('/api/search/image',data={'image':(io.BytesIO(b'not an image'),'fake.png')},headers={'X-CSRF-Token':token})
    assert r.status_code==400
    r=client.post('/api/search/image',data={'image':(io.BytesIO(b'x'*(5*1024*1024+1)),'big.png')},headers={'X-CSRF-Token':token})
    assert r.status_code==413
    with app.app_context():
        assert get_db().execute('SELECT COALESCE(SUM(quantity),0) FROM inventory_reservations').fetchone()[0]==0
        assert get_db().execute('SELECT count(*) FROM orders').fetchone()[0]==0
