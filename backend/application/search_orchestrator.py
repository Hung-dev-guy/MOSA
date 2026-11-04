from backend.data_infrastructure.adapters.image_embedding_adapter import encode_catalogue, encode_query
from backend.data_infrastructure.indexes import keyword_index, vector_index
from backend.data_infrastructure.storage.image_storage import image_path

from .catalogue_service import published_products


def catalogue(args,paginate=True):
    return keyword_index.search(published_products(),args,paginate)


def image_search(raw,args):
    query=encode_query(raw)
    candidates=[]
    for product in catalogue(args,paginate=False)['items']:
        path=image_path(product['image'])
        if path:
            candidates.append((product,encode_catalogue(path)))
    items=vector_index.rank(query,candidates)
    return {'items':items[:8],'total':len(items),'page':1,'pages':1,'method':'So khớp màu và bố cục; không đảm bảo đúng loại sản phẩm. Ảnh không được lưu.'}
