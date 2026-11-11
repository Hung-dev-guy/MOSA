"""Import public ADCBook catalogue facts and local images, with explicit demo stock.

Run without --apply to download and validate a plan without changing the database.
"""
import argparse
import hashlib
import io
import json
import re
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from uuid import NAMESPACE_URL, uuid5

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.data_infrastructure.database.connection import connect, init_db, now
from backend.shared.product_types import PRODUCT_FIELDS, PRODUCT_LABELS
from scripts.backup import backup
from scripts.update_product_descriptions import description

BASE = 'https://adcbook.net.vn/'
COLLECTIONS = {'pen':'but-viet', 'notebook':'so-cac-loai', 'bag':'cap-ba-lo-tui-xach',
               'toy':'do-choi', 'book':'sach-thieu-nhi', 'electric_device':'san-pham-dien-dien-tu'}
ASSETS = ROOT / 'frontend/public/assets/adcbook'
SOURCE = 'adcbook.net.vn'
USER_AGENT = 'MosaCatalogueImport/1.0'


def safe_url(value, image=False):
    url = urljoin(BASE, value)
    parsed = urlparse(url)
    hosts = {'adcbook.net.vn', 'www.adcbook.net.vn'}
    if image:
        hosts.add('bizweb.dktcdn.net')
    if parsed.scheme != 'https' or parsed.hostname not in hosts or parsed.username or parsed.password:
        raise ValueError('Unexpected source URL')
    return url


class Fetcher:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.last_request = 0

    def get(self, url, image=False):
        url = safe_url(url, image)
        path = self.directory / hashlib.sha256(url.encode()).hexdigest()
        if path.is_file():
            return path.read_bytes()
        time.sleep(max(0, .5 - (time.monotonic() - self.last_request)))
        request = urllib.request.Request(url, headers={'User-Agent':USER_AGENT})
        self.last_request = time.monotonic()
        with urllib.request.urlopen(request, timeout=30) as response:
            safe_url(response.geturl(), image)
            data = response.read(10 * 1024 * 1024 + 1)
        if len(data) > 10 * 1024 * 1024:
            raise ValueError('Source response exceeds 10 MB')
        path.write_bytes(data)
        return data


def tags_of(product):
    tags = {}
    for tag in product.get('tags', []):
        key, separator, value = str(tag).partition('_')
        if separator and value.strip():
            tags.setdefault(key.casefold(), []).append(value.strip())
    return tags


def tag_value(tags, *keys):
    for key in keys:
        if tags.get(key):
            return ', '.join(dict.fromkeys(tags[key]))
    return None


def minimum_age(tags):
    value = tag_value(tags, 'age') or tag_value(tags, 'dotuoi') or ''
    match = re.fullmatch(r'(\d+)\s*(?:\+|[-–]\s*\d+)?(?:\s*tuổi)?', value, re.I)
    return int(match[1]) if match else None


def normalized_product(product, variant, kind):
    """Use source facts, never guess mandatory size/page count/publisher or availability."""
    if kind not in PRODUCT_FIELDS:
        raise ValueError('Unknown product type')
    tags = tags_of(product)
    name = str(product.get('name') or '').strip()
    variant_name = str(variant.get('title') or '').strip()
    if not name or not variant.get('id') or not product.get('id'):
        raise ValueError('Missing source identity/name')
    if variant_name and variant_name.casefold() not in ['default title', 'default']:
        name += ' — ' + variant_name
    try:
        price = Decimal(str(variant.get('price')))
        if not price.is_finite() or price <= 0 or price != price.to_integral_value() or price > 10**12:
            raise ValueError('Invalid VND price')
    except (InvalidOperation, TypeError):
        raise ValueError('Invalid VND price') from None
    source_unit = str(variant.get('unit') or '').strip()
    unit = source_unit or ('Chiếc' if kind == 'electric_device' else '')
    if not unit or len(unit) > 30:
        raise ValueError('Missing/invalid selling unit')
    source_type = re.sub(r'\s*\([^)]*\)', '', str(product.get('product_type') or '')).strip()
    size = tag_value(tags, 'kichthuoc')
    details = {}
    if kind == 'pen':
        details = {'color':tag_value(tags, 'mausac'), 'type':source_type or 'Bút viết'}
    elif kind == 'notebook':
        pages = tag_value(tags, 'sotrang') or ''
        match = re.fullmatch(r'(\d+)\s*(?:trang|tr)?', pages, re.I)
        if not match or not size:
            raise ValueError('Notebook missing explicit page count/size')
        details = {'page_num':int(match[1]), 'size':size, 'type':source_type or 'Sổ'}
    elif kind == 'bag':
        if not size:
            raise ValueError('Bag missing explicit size')
        details = {'size':size, 'pattern':tag_value(tags, 'hoatiet')}
    elif kind == 'toy':
        public_tags = [t for t in product.get('tags', []) if '_' not in t and t.casefold() != 'đồ chơi']
        details = {'type':public_tags[-1] if public_tags else source_type or 'Đồ chơi', 'minimum_age':minimum_age(tags)}
    elif kind == 'book':
        publisher = tag_value(tags, 'nxb')
        if not publisher:
            raise ValueError('Book missing explicit publisher')
        details = {'category':source_type or 'Sách thiếu nhi', 'minimum_age':minimum_age(tags), 'publisher':publisher}
    else:
        weight = variant.get('weight')
        grams = Decimal(str(weight or 0)) * (1000 if variant.get('weight_unit') == 'kg' else 1)
        details = {'minimum_age':minimum_age(tags), 'weight':int(grams) if grams > 0 else None}
    for field, required in PRODUCT_FIELDS[kind].items():
        value = details.get(field)
        maximum = 150 if field == 'publisher' else 100 if field in ['category','pattern'] else 50
        if required and (value is None or value == ''):
            raise ValueError('Missing subtype field: ' + field)
        if isinstance(value, str) and len(value) > maximum:
            raise ValueError('Subtype field too long: ' + field)
        if isinstance(value, int) and (value < (1 if field == 'page_num' else 0) or value > 1000000):
            raise ValueError('Invalid subtype number: ' + field)
    source_url = safe_url(variant.get('url') or product.get('url') or '/' + product['alias'])
    image = variant.get('featured_image') or {}
    image_url = image.get('src') if isinstance(image, dict) else image
    image_url = safe_url(image_url or product.get('featured_image') or '', image=True)
    if image_url == BASE:
        raise ValueError('Missing product image')
    brand = tag_value(tags, 'thuonghieu') or ''
    origin = tag_value(tags, 'xuatxu')
    material = tag_value(tags, 'chatlieu')
    attrs = {}
    for label,value in [('SKU',variant.get('sku')),('Mã vạch',variant.get('barcode')),
                        ('Kích thước',size),('Độ tuổi',tag_value(tags,'age')),
                        ('Nhà cung cấp',product.get('vendor'))]:
        if value:
            attrs[label] = str(value)[:100]
    return {'id':str(uuid5(NAMESPACE_URL, f'{BASE}variant/{variant["id"]}')),
            'name':name[:200], 'source_name':name, 'product_type':kind,
            'price':int(price), 'selling_unit':unit, 'source_selling_unit':source_unit or None, 'brand':brand[:100],
            'origin':origin[:100] if origin else None, 'material':material[:100] if material else None,
            'description':description({'name': name, 'product_type': kind}), 'attributes':attrs, 'details':details,
            'source_product_id':str(product['id']), 'source_variant_id':str(variant['id']),
            'source_url':source_url, 'source_image_url':image_url,
            'source_available':bool(variant.get('available')), 'image':None}


def download_image(fetcher, url, directory=ASSETS):
    data = fetcher.get(url, image=True)
    with Image.open(io.BytesIO(data)) as image:
        extensions = {'JPEG':'jpg', 'PNG':'png', 'WEBP':'webp'}
        if image.format not in extensions or image.width * image.height > 16000000:
            raise ValueError('Unsupported image format/size')
        extension = extensions[image.format]
        image.verify()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    filename = hashlib.sha256(url.encode()).hexdigest()[:24] + '.' + extension
    path = directory / filename
    if not path.is_file():
        path.write_bytes(data)
    return '/assets/adcbook/' + filename


def collect(fetcher, per_type):
    robots = RobotFileParser()
    robots.parse(fetcher.get(BASE + 'robots.txt').decode().splitlines())
    records, skipped, seen = [], [], set()
    for kind, slug in COLLECTIONS.items():
        count = 0
        for page in range(1, 9):
            url = f'{BASE}collections/{slug}/products.json?limit=50&page={page}'
            if not robots.can_fetch(USER_AGENT, url):
                raise ValueError('Collection is disallowed by robots.txt')
            products = json.loads(fetcher.get(url)).get('products', [])
            if not products:
                break
            for product in products:
                for variant in product.get('variants', []):
                    source_id = str(variant.get('id'))
                    if source_id in seen:
                        continue
                    try:
                        item = normalized_product(product, variant, kind)
                        item['image'] = download_image(fetcher, item['source_image_url'])
                    except (ValueError, OSError) as error:
                        skipped.append({'kind':kind,'product_id':product.get('id'),'variant_id':variant.get('id'),'reason':str(error)})
                        continue
                    records.append(item)
                    seen.add(source_id)
                    count += 1
                    if count >= per_type:
                        break
                if count >= per_type:
                    break
            if count >= per_type:
                break
        print(f'{kind}: {count} SKU ready', flush=True)
    return records, skipped


def apply_records(db, records, stock, source=SOURCE):
    if type(stock) is not int or stock < 1:
        raise ValueError('Demo available stock must be positive')
    seen = set()
    with db:
        db.execute('BEGIN IMMEDIATE')
        for item in records:
            pid, kind = item['id'], item['product_type']
            if kind not in PRODUCT_FIELDS or pid in seen or not item['image']:
                raise ValueError('Invalid/duplicate import record')
            seen.add(pid)
            previous = db.execute('SELECT stock FROM products WHERE id=?', (pid,)).fetchone()
            reserved = db.execute('SELECT COALESCE(SUM(quantity),0) FROM inventory_reservations WHERE product_id=?', (pid,)).fetchone()[0]
            on_hand = reserved + stock
            values = (pid,item['name'],item['description'],item['brand'],item['price'],item['selling_unit'],json.dumps(item['attributes'],ensure_ascii=False),item['image'],kind,on_hand,item['origin'],item['material'])
            db.execute("INSERT INTO products(id,name,description,brand,price,selling_unit,attributes,image,product_type,stock,origin,material,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'ACTIVE') ON CONFLICT(id) DO UPDATE SET name=excluded.name,description=excluded.description,brand=excluded.brand,price=excluded.price,selling_unit=excluded.selling_unit,attributes=excluded.attributes,image=excluded.image,product_type=excluded.product_type,stock=excluded.stock,origin=excluded.origin,material=excluded.material,status='ACTIVE'", values)
            for table in PRODUCT_FIELDS:
                db.execute('DELETE FROM ' + table + ' WHERE product_id=?', (pid,))
            fields = item['details']
            db.execute('INSERT INTO '+kind+'(product_id,'+','.join(fields)+') VALUES('+','.join('?' for _ in range(len(fields)+1))+')', (pid,*fields.values()))
            db.execute('UPDATE product_image SET is_primary=0 WHERE product_id=?', (pid,))
            db.execute('INSERT INTO product_image(product_id,image_url,is_primary) VALUES(?,?,1) ON CONFLICT(product_id,image_url) DO UPDATE SET is_primary=1', (pid,item['image']))
            db.execute('INSERT INTO catalogue_sources(product_id,source,source_product_id,source_variant_id,source_url,source_name,source_image_url,source_available,demo_available,imported_at) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(product_id) DO UPDATE SET source_url=excluded.source_url,source_name=excluded.source_name,source_image_url=excluded.source_image_url,source_available=excluded.source_available,demo_available=excluded.demo_available,imported_at=excluded.imported_at', (pid,source,item['source_product_id'],item['source_variant_id'],item['source_url'],item['source_name'],item['source_image_url'],int(item['source_available']),stock,now()))
            delta = on_hand - (previous['stock'] if previous else 0)
            if delta:
                db.execute('INSERT INTO inventory_movements(product_id,quantity,kind,reason,actor,created_at) VALUES(?,?,?,?,?,?)', (pid,delta,'import',source + ' import: explicit demo available stock',source + '-import',now()))
        db.execute('INSERT INTO audit(actor,action,record,created_at) VALUES(?,?,?,?)', (source + '-import','catalogue.import',json.dumps({'source':source,'count':len(records),'demo_available':stock}),now()))
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Import failed foreign-key validation')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=ROOT/'instance/mosa.sqlite')
    parser.add_argument('--per-type', type=int, default=20)
    parser.add_argument('--stock', type=int, default=100)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.per_type <= 250 or not 1 <= args.stock <= 100000:
        parser.error('per-type must be 1..250; stock must be 1..100000')
    records, skipped = collect(Fetcher(ROOT/'.test-runtime/adcbook-cache'), args.per_type)
    counts = dict(Counter(item['product_type'] for item in records))
    if any(counts.get(kind,0) != args.per_type for kind in COLLECTIONS):
        raise RuntimeError('Not enough valid products in all six types; database was not changed')
    backup_path = None
    if args.apply:
        if args.database.exists():
            suffix = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            backup_path = Path(str(args.database)+'.pre-adcbook-'+suffix+'.sqlite')
            backup(args.database, backup_path)
        init_db(args.database, demo=False)
        db = connect(args.database)
        try:
            apply_records(db, records, args.stock)
        finally:
            db.close()
    report = {'source':BASE,'imported_at':now(),'applied':args.apply,'database':str(args.database),
              'backup':str(backup_path) if backup_path else None,'counts':counts,
              'available_per_sku':args.stock,'availability_is_demo':True,'skipped':skipped,'items':records}
    path = ROOT/'docs/adcbook-import.json'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'applied':args.apply,'counts':counts,'total':len(records),'skipped':len(skipped),'report':str(path),'backup':report['backup']},ensure_ascii=False),flush=True)


if __name__ == '__main__':
    main()
