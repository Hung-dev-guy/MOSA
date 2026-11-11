"""Deterministic keyword retrieval/filtering over current catalogue records."""
import json
import unicodedata

from backend.shared.validation import require
from backend.shared.product_types import PRODUCT_FIELDS


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFD',value.lower().replace('đ','d')) if unicodedata.category(c)!='Mn')


def search(items,args,paginate=True):
    require('category' not in args, 'Bộ lọc danh mục cũ đã bỏ. Chọn loại sản phẩm và tìm lại.')
    kind=args.get('product_type')
    require(not kind or kind in PRODUCT_FIELDS, 'Loại sản phẩm không hợp lệ.')
    if kind:
        items=[p for p in items if p['product_type']==kind]
    query=normalize(args.get('q','').strip())
    if query:
        items=[p for p in items if all(word in normalize(p['name']+' '+p['brand']+' '+json.dumps({**p['attributes'],**p['details']},ensure_ascii=False)) for word in query.split())]
    for key,field in [('brand','brand')]:
        if args.get(key):
            items=[p for p in items if str(p[field])==args[key]]
    for key,compare in [('min_price',lambda a,b:a>=b),('max_price',lambda a,b:a<=b)]:
        if args.get(key):
            require(args[key].isdigit(),'Khoảng giá không hợp lệ.')
            items=[p for p in items if compare(p['price'],int(args[key]))]
    if args.get('available')=='1':
        items=[p for p in items if p['available']>0]
    if args.get('attribute'):
        parts=args['attribute'].split(':',1)
        require(len(parts)==2,'Thuộc tính có dạng tên:giá trị.')
        items=[p for p in items if normalize(str(p['details'].get({'màu':'color','khổ':'size','trang':'page_num'}.get(parts[0],parts[0]),p['attributes'].get(parts[0],'')) or ''))==normalize(parts[1])]
    for key in ['color','size','minimum_age','publisher']:
        if args.get(key):
            value=args[key]
            if key=='minimum_age':
                require(value.isdigit(),'Độ tuổi không hợp lệ.')
                items=[p for p in items if p['details'].get(key) is not None and p['details'][key]<=int(value)]
            else:
                items=[p for p in items if normalize(str(p['details'].get(key) or p['attributes'].get({'color':'màu','size':'khổ'}.get(key,key),'')))==normalize(value)]
    sort=args.get('sort','newest')
    require(sort in ['newest','price_asc','price_desc','name'],'Sắp xếp không hợp lệ.')
    items.sort(key=lambda p:p['price'] if sort.startswith('price') else p['name'] if sort=='name' else p['created_at'],reverse=sort in ['newest','price_desc'])
    page=args.get('page','1')
    require(page.isdigit() and int(page)>0,'Trang không hợp lệ.')
    page=int(page)
    return {'items':items[(page-1)*8:page*8] if paginate else items,'total':len(items),'page':page,'pages':max(1,(len(items)+7)//8)}
