from datetime import datetime, timezone, timedelta
from uuid import uuid4

from backend.data_infrastructure.adapters.image_embedding_adapter import encode_catalogue, encode_query
from backend.data_infrastructure.indexes import keyword_index, vector_index, semantic_index
from backend.data_infrastructure.storage.image_storage import image_path
from backend.data_infrastructure.database.connection import get_db, now
from backend.shared.validation import require, text
from .catalog_service import published_products


FILTERS = {'product_type':'CATEGORY','brand':'BRAND','min_price':'MIN_PRICE','max_price':'MAX_PRICE','available':'AVAILABLE','color':'COLOR','size':'SIZE','minimum_age':'MINIMUM_AGE','publisher':'PUBLISHER'}


def record_search(result, args, modality, customer_id=None, guest_owner=None, media=None):
    db = get_db()
    raw = text(args.get('q',''), 'Từ khóa', 0, 500)
    query_id = str(uuid4())
    # Keep only retrieval input, never account/order data. Old logs expire after 24 hours.
    cutoff = (datetime.now(timezone.utc)-timedelta(days=1)).isoformat(timespec='seconds')
    db.execute('DELETE FROM search_query WHERE created_at<?', (cutoff,))
    encoder = 'color-layout-v1' if media else result.get('encoder_version', 'keyword-v1')
    db.execute('INSERT INTO search_query(query_id,customer_id,guest_owner,modality,raw_text,normalized_text,language,encoder_version) VALUES(?,?,?,?,?,?,?,?)', (query_id,customer_id,guest_owner if not customer_id else None,modality,raw,keyword_index.normalize(raw),'vi',encoder))
    for key,kind in FILTERS.items():
        if args.get(key):
            db.execute('INSERT INTO search_filter(query_id,filter_type,filter_value) VALUES(?,?,?)', (query_id,kind,text(str(args[key]), 'Bộ lọc', 1, 255)))
    if args.get('attribute'):
        key,value=args['attribute'].split(':',1)
        kind={'màu':'COLOR','color':'COLOR','khổ':'SIZE','size':'SIZE','publisher':'PUBLISHER','minimum_age':'MINIMUM_AGE'}.get(key)
        if kind:
            db.execute('INSERT INTO search_filter(query_id,filter_type,filter_value) VALUES(?,?,?)', (query_id,kind,value))
    offset=(result['page']-1)*8
    for rank,p in enumerate(result['items'],offset+1):
        score=p.get('similarity',1.0)
        explanation = 'Color/layout similarity' if media else 'Semantic text cosine similarity' if result.get('search_mode') == 'semantic' else 'Explicit keyword and attribute matching'
        db.execute('INSERT INTO search_result(query_id,product_id,rank_position,relevance_score,final_score,explanation) VALUES(?,?,?,?,?,?)', (query_id,p['id'],rank,score,score,explanation))
    if media:
        db.execute('INSERT INTO query_media(query_id,media_type,storage_reference,mime_type,file_size_bytes,expires_at) VALUES(?,?,?,?,?,?)', (query_id,'IMAGE',media['reference'],media['mime_type'],media['size'],media['expires_at']))
    db.commit()
    return {**result,'query_id':query_id,'modality':modality}


def catalogue(args,paginate=True,customer_id=None,guest_owner=None):
    query = text(args.get('q',''), 'Từ khóa', 0, 500)
    mode = args.get('search_mode', 'keyword')
    require(mode in ['keyword', 'semantic'], 'Chế độ tìm kiếm không hợp lệ.')
    modality=args.get('modality','TEXT')
    require(modality in ['TEXT','VOICE'], 'Loại truy vấn không hợp lệ.')
    if mode == 'semantic' and query:
        result = semantic_index.search(published_products(), args, paginate)
    else:
        result = {**keyword_index.search(published_products(), args, paginate), 'search_mode': 'keyword'}
    if not paginate:
        return result
    if args.get('q') or any(args.get(k) for k in FILTERS) or args.get('attribute'):
        return record_search(result,args,modality,customer_id,guest_owner)
    return result


def image_search(raw,args,customer_id=None,guest_owner=None,media_directory=None):
    query=encode_query(raw)
    candidates=[]
    for p in catalogue(args,paginate=False)['items']:
        path=image_path(p['image'])
        if path:
            candidates.append((p,encode_catalogue(path)))
    items=vector_index.rank(query,candidates)
    result={'items':items[:8],'total':len(items),'page':1,'pages':1,'method':'So khớp màu và bố cục; không đảm bảo đúng loại sản phẩm.'}
    if media_directory is not None:
        from backend.data_infrastructure.storage.image_storage import store_query_image
        media=store_query_image(raw,media_directory)
        return record_search(result,args,'MULTIMODAL' if args.get('q') else 'IMAGE',customer_id,guest_owner,media)
    return result
