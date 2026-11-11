import io
import pytest
from PIL import Image
from scripts import import_tiki


def test_tiki_normalization_requires_price_and_real_publisher(monkeypatch, tmp_path):
    image = io.BytesIO()
    Image.new('RGB', (8, 8)).save(image, format='PNG')
    monkeypatch.setattr(import_tiki, 'get', lambda url: image.getvalue())
    monkeypatch.setattr(import_tiki, 'ASSETS', tmp_path)
    product = {'id': 123, 'name': 'Book', 'price': 10000, 'thumbnail_url': 'https://salt.tikicdn.com/a.png',
               'specifications': [{'attributes': [{'code': 'manufacturer', 'value': 'Publisher'}]}]}
    a = import_tiki.normalize(product, 'book', 'Books')
    assert a['price'] == 10000 and a['details']['publisher'] == 'Publisher'
    assert a['id'] == import_tiki.normalize(product, 'book', 'Books')['id']
    assert (tmp_path / '123.png').exists()
    for bad in [0, -1, 1.5, float('inf')]:
        with pytest.raises(ValueError):
            import_tiki.normalize({**product, 'price': bad}, 'book', 'Books')
    with pytest.raises(ValueError, match='publisher'):
        import_tiki.normalize({**product, 'specifications': []}, 'book', 'Books')
