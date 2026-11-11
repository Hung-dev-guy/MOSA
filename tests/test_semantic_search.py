import pytest

from backend.data_infrastructure.adapters import text_embedding_adapter
from backend.data_infrastructure.database.connection import get_db
from backend.data_infrastructure.indexes import semantic_index


@pytest.fixture
def embeddings(monkeypatch):
    # Deliberately independent of query words: exercise vector retrieval, not substring matching.
    monkeypatch.setattr(text_embedding_adapter, 'encode_documents', lambda docs: [(1.0, 0.0) for _ in docs])
    monkeypatch.setattr(text_embedding_adapter, 'encode_query', lambda query: (0.9, 0.19**0.5))


def test_semantic_mode_filters_pagination_logs_and_current_catalogue(app, client, embeddings):
    args = {'q': 'vật dụng cho nhu cầu của tôi', 'search_mode': 'semantic',
            'product_type': 'pen', 'brand': 'Thiên Long', 'max_price': '15000', 'available': '1'}
    assert client.get('/api/products', query_string={**args, 'search_mode': 'keyword'}).json['total'] == 0
    response = client.get('/api/products', query_string=args)
    assert response.status_code == 200
    result = response.json
    assert result['search_mode'] == 'semantic'
    assert result['items'] and all(p['product_type'] == 'pen' and p['brand'] == 'Thiên Long'
                                   and p['price'] <= 15000 and p['available'] > 0 for p in result['items'])
    assert result['items'][0]['similarity'] == pytest.approx(0.9)
    pid = result['items'][0]['id']
    with app.app_context():
        db = get_db()
        query = db.execute('SELECT * FROM search_query WHERE query_id=?', (result['query_id'],)).fetchone()
        assert query['modality'] == 'TEXT' and query['encoder_version'] == text_embedding_adapter.MODEL_VERSION
        row = db.execute('SELECT * FROM search_result WHERE query_id=?', (result['query_id'],)).fetchone()
        assert row['relevance_score'] == pytest.approx(0.9)
        assert row['explanation'] == 'Semantic text cosine similarity'
        assert db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM inventory_reservations').fetchone()[0] == 0
        db.execute('UPDATE products SET price=12000 WHERE id=?', (pid,))
        db.commit()
    updated = client.get('/api/products', query_string=args).json
    assert next(p for p in updated['items'] if p['id'] == pid)['price'] == 12000
    with app.app_context():
        get_db().execute("UPDATE products SET status='ARCHIVED' WHERE id=?", (pid,))
        get_db().commit()
    assert pid not in [p['id'] for p in client.get('/api/products', query_string=args).json['items']]
    voice = client.get('/api/products', query_string={**args, 'modality': 'VOICE'}).json
    assert voice['modality'] == 'VOICE' and voice['search_mode'] == 'semantic'
    first = client.get('/api/products', query_string={'q': 'nhu cầu', 'search_mode': 'semantic'}).json
    second = client.get('/api/products', query_string={'q': 'nhu cầu', 'search_mode': 'semantic', 'page': '2'}).json
    assert first['total'] > 8 and second['items']
    assert not {p['id'] for p in first['items']} & {p['id'] for p in second['items']}
    sorted_result = client.get('/api/products', query_string={'q': 'nhu cầu', 'search_mode': 'semantic', 'sort': 'price_asc'}).json
    prices = [p['price'] for p in sorted_result['items']]
    assert prices == sorted(prices)


def test_semantic_ranks_by_cosine_and_drops_unrelated_results(monkeypatch):
    items = [{'id': str(i), 'name': str(i), 'brand': '', 'attributes': {}, 'details': {},
              'created_at': str(i), 'price': i+1} for i in range(3)]
    monkeypatch.setattr(text_embedding_adapter, 'encode_documents', lambda docs: [(0, 1), (3, 1), (1, 0)])
    monkeypatch.setattr(text_embedding_adapter, 'encode_query', lambda query: (1, 0))
    result = semantic_index.search(items, {'q': 'different wording'})
    assert [p['id'] for p in result['items']] == ['0', '1']
    assert result['items'][0]['similarity'] == 1.0
    monkeypatch.setattr(text_embedding_adapter, 'encode_query', lambda query: (-1, 0))
    assert semantic_index.search(items, {'q': 'unrelated'})['total'] == 0


def test_semantic_failure_is_explicit_and_keyword_still_works(client, monkeypatch):
    def unavailable(docs):
        raise RuntimeError('missing model')
    monkeypatch.setattr(text_embedding_adapter, 'encode_documents', unavailable)
    response = client.get('/api/products?q=bút&search_mode=semantic')
    assert response.status_code == 503
    assert 'từ khóa' in response.json['error']
    assert client.get('/api/products?q=bút&search_mode=keyword').json['total'] > 0


@pytest.mark.parametrize('query', [
    'q=bút&search_mode=invalid', 'q=bút&search_mode=semantic&page=-1',
    'q=bút&search_mode=semantic&min_price=oops', 'q=bút&search_mode=semantic&sort=invalid',
    'q=bút&search_mode=semantic&product_type=invalid', 'q=bút&search_mode=semantic&modality=invalid',
    'q=' + 'x'*501 + '&search_mode=semantic',
])
def test_invalid_semantic_requests_do_not_run_model(client, monkeypatch, query):
    def unexpected(docs):
        pytest.fail('Invalid input reached embedding model')
    monkeypatch.setattr(text_embedding_adapter, 'encode_documents', unexpected)
    assert client.get('/api/products?' + query).status_code == 400


def test_empty_semantic_query_browses_without_loading_model(client, monkeypatch):
    def unexpected(docs):
        pytest.fail('Empty query reached embedding model')
    monkeypatch.setattr(text_embedding_adapter, 'encode_documents', unexpected)
    assert client.get('/api/products?search_mode=semantic').json['total'] > 0


def test_e5_prefixes_and_document_cache(monkeypatch):
    calls = []
    class Encoder:
        def embed(self, documents, **kwargs):
            calls.append(list(documents))
            return iter([(1.0, 0.0)] * len(documents))
    monkeypatch.setattr(text_embedding_adapter, 'load_model', lambda: Encoder())
    text_embedding_adapter.encode_documents.cache_clear()
    try:
        text_embedding_adapter.encode_documents(('Sổ tay', 'Bút'))
        text_embedding_adapter.encode_documents(('Sổ tay', 'Bút'))
        text_embedding_adapter.encode_query('ghi chép')
        assert calls == [['passage: Sổ tay', 'passage: Bút'], ['query: ghi chép']]
    finally:
        text_embedding_adapter.encode_documents.cache_clear()


def test_e5_demo_cutoff_drops_high_but_insufficient_cosine(monkeypatch):
    items = [{'id': '1', 'name': 'Product', 'brand': '', 'attributes': {}, 'details': {}, 'price': 1, 'created_at': '2026-11-11'}]
    monkeypatch.setattr(text_embedding_adapter, 'encode_documents', lambda docs: [(1.0, 0.0)])
    monkeypatch.setattr(text_embedding_adapter, 'encode_query', lambda query: (0.84, (1-0.84**2)**0.5))
    assert semantic_index.search(items, {'q': 'query'})['total'] == 0
    monkeypatch.setattr(text_embedding_adapter, 'encode_query', lambda query: (0.86, (1-0.86**2)**0.5))
    assert semantic_index.search(items, {'q': 'query'})['total'] == 1
