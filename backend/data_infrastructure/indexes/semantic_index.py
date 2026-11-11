"""Cosine retrieval over published catalogue text, with explicit filters preserved."""
import json
import logging
import math
from threading import Lock

from backend.data_infrastructure.adapters import text_embedding_adapter
from backend.shared.validation import Problem
from . import keyword_index


# shortcut: demo relevance cutoff, calibrate on labelled Vietnamese queries before production.
MIN_SIMILARITY = 0.85
_inference_lock = Lock()


def document(product):
    return ' '.join([
        product['name'], product['brand'], product.get('selling_unit', ''),
        json.dumps({**product['attributes'], **product['details']}, ensure_ascii=False, sort_keys=True),
        product.get('description', ''),
    ])


def search(items, args, paginate=True):
    sort = args.get('sort', 'relevance')
    filters = {**args, 'q': '', 'sort': 'newest' if sort == 'relevance' else sort}
    result = keyword_index.search(items, filters, paginate=False)
    candidates = result['items']
    ranked = []
    if candidates:
        try:
            with _inference_lock:
                vectors = text_embedding_adapter.encode_documents(tuple(document(p) for p in candidates))
                query = text_embedding_adapter.encode_query(args['q'].strip())
            query_norm = math.sqrt(sum(float(v)**2 for v in query))
            for product, vector in zip(candidates, vectors, strict=True):
                norm = query_norm * math.sqrt(sum(float(v)**2 for v in vector))
                score = sum(float(a)*float(b) for a,b in zip(query,vector,strict=True)) / norm if norm else 0
                if score >= MIN_SIMILARITY:
                    ranked.append({**product, 'similarity': round(score, 6)})
        except Exception as error:
            logging.getLogger(__name__).exception('Semantic text search unavailable')
            raise Problem('Tìm ngữ nghĩa chưa sẵn sàng. Hãy thử lại hoặc chuyển sang tìm từ khóa.', 503) from error
    if sort == 'relevance':
        ranked.sort(key=lambda p: (-p['similarity'], p['id']))
    page = result['page']
    return {**result, 'items': ranked[(page-1)*8:page*8] if paginate else ranked,
            'total': len(ranked), 'pages': max(1, (len(ranked)+7)//8),
            'search_mode': 'semantic', 'encoder_version': text_embedding_adapter.MODEL_VERSION}
