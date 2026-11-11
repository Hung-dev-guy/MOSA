"""Collect public Tiki product facts, local images, and explicit demo inventory."""
import argparse
import hashlib
import io
import json
import math
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.robotparser import RobotFileParser
from uuid import NAMESPACE_URL, uuid5

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.import_adcbook import apply_records
from scripts.backup import backup
from scripts.update_product_descriptions import description
from backend.data_infrastructure.database.connection import connect, now

HEADERS = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://tiki.vn/'}
CACHE = ROOT / '.test-runtime/tiki-cache'
ASSETS = ROOT / 'frontend/public/assets/tiki'


def get(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in {'tiki.vn', 'salt.tikicdn.com'}:
        raise ValueError('Unexpected source host')
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / hashlib.sha256(url.encode()).hexdigest()
    if path.exists():
        return path.read_bytes()
    time.sleep(.3)
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=25) as response:
        if urlparse(response.geturl()).hostname != parsed.hostname:
            raise ValueError('Unexpected redirect')
        data = response.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024:
        raise ValueError('Response too large')
    path.write_bytes(data)
    return data


def normalize(d, kind, category):
    specs = {a['code']: str(a.get('value') or '').strip() for group in d.get('specifications', []) for a in group.get('attributes', [])}
    price = d.get('price')
    if not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0 or price > 10**12 or price != int(price):
        raise ValueError('Invalid price')
    size = specs.get('dimensions') or specs.get('size')
    if kind == 'book':
        publisher = specs.get('manufacturer')
        if not publisher:
            raise ValueError('Missing publisher')
        details = {'category': category[:100], 'publisher': publisher[:150], 'minimum_age': None}
    elif kind == 'pen':
        details = {'type': 'Bút viết', 'color': None}
    elif kind == 'toy':
        details = {'type': 'Đồ chơi', 'minimum_age': None}
    elif kind == 'bag':
        if not size:
            raise ValueError('Missing bag size')
        details = {'size': size[:50], 'pattern': None}
    elif kind == 'notebook':
        pages = specs.get('number_of_page', '')
        match = re.fullmatch(r'(\d+)\s*(?:trang)?', pages)
        if not size or not match:
            raise ValueError('Missing notebook pages/size')
        details = {'page_num': int(match[1]), 'size': size[:50], 'type': 'Sổ / vở'}
    else:
        details = {'minimum_age': None, 'weight': None}
    image_url = (d.get('thumbnail_url') or '').replace('http://', 'https://')
    raw = get(image_url)
    with Image.open(io.BytesIO(raw)) as im:
        if im.width * im.height > 16000000 or im.format not in {'JPEG', 'PNG', 'WEBP'}:
            raise ValueError('Invalid image')
        ext = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp'}[im.format]
        im.verify()
    ASSETS.mkdir(parents=True, exist_ok=True)
    filename = str(d['id']) + '.' + ext
    (ASSETS / filename).write_bytes(raw)
    source_url = 'https://tiki.vn/' + (d.get('url_key') or ('product-p' + str(d['id']))) + '.html'
    unit = {'book': 'Cuốn', 'notebook': 'Quyển', 'pen': 'Sản phẩm', 'bag': 'Chiếc', 'toy': 'Sản phẩm', 'electric_device': 'Chiếc'}[kind]
    return {'id': str(uuid5(NAMESPACE_URL, 'https://tiki.vn/product/' + str(d['id']))),
            'name': d['name'][:200], 'source_name': d['name'], 'description': description({'name': d['name'], 'product_type': kind}),
            'brand': str((d.get('brand') or {}).get('name') or '')[:100], 'price': int(price), 'selling_unit': unit,
            'attributes': {'Nguồn': source_url, 'Danh mục nguồn': category, 'Tồn kho': 'Demo'},
            'image': '/assets/tiki/' + filename, 'product_type': kind, 'origin': specs.get('origin', '')[:100] or None,
            'material': specs.get('material', '')[:100] or None, 'details': details,
            'source_product_id': str(d['id']), 'source_variant_id': str(d['id']), 'source_url': source_url,
            'source_image_url': image_url, 'source_available': d.get('inventory_status') == 'available'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    robots = RobotFileParser()
    robots.parse(get('https://tiki.vn/robots.txt').decode().splitlines())
    groups = [('book', 316, 'Sách tiếng Việt', 60, None), ('pen', 1858, 'Bút viết', 45, None),
              ('toy', 5250, 'Đồ chơi', 45, None), ('bag', 5674, 'Balo học sinh', 30, None),
              ('notebook', 8322, 'Sổ tay', 20, 'sổ tay'),
              ('electric_device', 8322, 'Máy tính cầm tay', 20, 'máy tính cầm tay')]
    records, skipped, seen = [], [], set()
    for kind, cid, label, target, query in groups:
        count = 0
        for page in range(1, 7):
            params = {'limit': 40, 'category': cid, 'page': page}
            if query:
                params['q'] = query
            url = 'https://tiki.vn/api/personalish/v1/blocks/listings?' + urlencode(params)
            if not robots.can_fetch('MosaCatalogueImport', url):
                raise ValueError('Robots disallows listing')
            products = json.loads(get(url)).get('data', [])
            if not products:
                break
            for item in products:
                pid = item['id']
                if pid in seen:
                    continue
                seen.add(pid)
                detail_url = 'https://tiki.vn/api/v2/products/' + str(pid)
                if not robots.can_fetch('MosaCatalogueImport', detail_url):
                    raise ValueError('Robots disallows product')
                try:
                    d = json.loads(get(detail_url))
                    # Search results must match the requested specialization.
                    if query and not any(word in d['name'].lower() for word in (['sổ', 'vở'] if kind == 'notebook' else ['máy tính'])):
                        continue
                    record = normalize(d, kind, label)
                    records.append(record)
                    count += 1
                except (ValueError, OSError, KeyError) as error:
                    skipped.append({'id': pid, 'kind': kind, 'reason': str(error)})
                if count >= target:
                    break
            print(kind, count, 'total', len(records), flush=True)
            if count >= target:
                break
    report = {'source': 'https://tiki.vn/', 'imported_at': now(), 'applied': False, 'counts': dict(Counter(r['product_type'] for r in records)),
              'availability_is_demo': True, 'demo_stock': 100, 'skipped': skipped, 'items': records}
    path = ROOT / 'docs/tiki-import.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if len(records) < 200:
        raise RuntimeError('Fewer than 200 valid products; database unchanged')
    if args.apply:
        database = ROOT / 'instance/mosa.sqlite'
        destination = Path(str(database) + '.pre-tiki-' + str(time.time_ns()) + '.sqlite')
        backup(database, destination)
        db = connect(database)
        try:
            fresh = [r for r in records if not db.execute('SELECT 1 FROM products WHERE id=?', (r['id'],)).fetchone()]
            apply_records(db, fresh, 100, source='tiki.vn')
            report.update(applied=True, added=len(fresh), backup=str(destination))
        finally:
            db.close()
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in {'items', 'skipped'}}, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
