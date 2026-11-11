from pathlib import Path


def test_production_bundle_and_spa_route(client):
    dist=Path(__file__).resolve().parents[1]/'frontend/dist'
    if not dist.exists():
        import pytest
        pytest.skip('Build frontend before production serving test')
    assert client.get('/product/6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086').status_code==200
    for p in (dist/'assets').rglob('*'):
        if p.is_file():
            assert client.get('/assets/'+p.relative_to(dist/'assets').as_posix()).status_code==200
    assert client.get('/assets/pen-blue.png').status_code==200
    assert client.get('/api/not-real').status_code==404
