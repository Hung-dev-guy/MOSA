from pathlib import Path


def test_production_bundle_and_spa_route(client):
    dist=Path(__file__).resolve().parents[1]/'frontend/dist'
    if not dist.exists():
        import pytest
        pytest.skip('Build frontend before production serving test')
    assert client.get('/product/1').status_code==200
    for p in (dist/'assets').iterdir():
        assert client.get('/assets/'+p.name).status_code==200
    assert client.get('/assets/pen-blue.png').status_code==200
    assert client.get('/api/not-real').status_code==404
