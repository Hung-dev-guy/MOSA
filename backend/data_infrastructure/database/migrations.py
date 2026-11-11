"""Transactional upgrade of the original demo database; keep a pre-upgrade backup."""
import json
import sqlite3
from pathlib import Path
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL


def legacy_id(table, value):
    if value is None:
        return None
    try:
        return str(UUID(str(value)))
    except ValueError:
        return str(uuid5(NAMESPACE_URL, f'mosa:{table}:{value}'))


def _upgrade_v1(db, path, schema):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'").fetchone():
        db.executescript(schema)
        return
    if db.execute('PRAGMA user_version').fetchone()[0] >= 2:
        db.executescript(schema)
        return
    backup = Path(str(path) + '.pre-design-v2.sqlite')
    if backup.exists():
        raise RuntimeError(f'Backup already exists: {backup}. Check the previous migration before retrying.')
    with sqlite3.connect(backup) as target:
        db.backup(target)
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    source = {t: [dict(r) for r in db.execute(f'SELECT * FROM "{t}"')] for t in tables}
    refs = {'user_id': 'users', 'customer_id': 'users', 'product_id': 'products', 'order_id': 'orders', 'category_id': 'categories', 'parent_id': 'categories'}
    db.execute('PRAGMA foreign_keys=OFF')
    try:
        db.executescript('BEGIN IMMEDIATE;\n' + '\n'.join(f'DROP TABLE "{t}";' for t in reversed(tables)) + '\n' + schema)
        for table in tables:
            if table == 'cart_items':
                continue
            allowed = {r[1] for r in db.execute(f'PRAGMA table_info("{table}")')}
            for old in source[table]:
                row = dict(old)
                if 'id' in row:
                    row['id'] = legacy_id(table, row['id'])
                for column, parent in refs.items():
                    if column in row:
                        row[column] = legacy_id(parent, row[column])
                if table == 'products':
                    attrs = json.loads(row['attributes'])
                    attrs['pack_quantity'] = row.pop('pack_quantity', 1)
                    row['attributes'] = json.dumps(attrs, ensure_ascii=False)
                    row['status'] = 'ACTIVE' if row.pop('published') else 'ARCHIVED'
                    row.pop('reserved', None)
                    # Legacy school supplies are not silently relabelled as toys/books.
                    kind = 'pen' if old['category_id'] == 1 else 'notebook' if old['category_id'] == 2 else None
                    row['product_type'] = kind
                if table == 'order_items':
                    row['snapshot_details'] = json.dumps({'pack_quantity': row.pop('pack_quantity', 1)})
                if table == 'payments':
                    row['id'] = str(uuid4())
                    row['method'] = 'COD' if row['method'] == 'cod' else 'ONLINE'
                    row['status'] = {'success': 'PAID', 'collected': 'PAID', 'failed': 'FAILED', 'cancelled': 'FAILED', 'pending': 'PENDING', 'awaiting_collection': 'PENDING'}[row['status']]
                    row['idempotency_key'] = 'migrated:' + row['order_id']
                if table == 'audit':
                    row['actor'] = legacy_id('users', row['actor']) if str(row['actor']).isdigit() else row['actor']
                row = {k: v for k, v in row.items() if k in allowed}
                db.execute(f'INSERT INTO "{table}" ({",".join(row)}) VALUES({",".join("?" for _ in row)})', tuple(row.values()))
        for row in source.get('users', []):
            uid = legacy_id('users', row['id'])
            db.execute('INSERT INTO carts(owner,customer_id) VALUES(?,?)', ('u:' + uid, uid))
        for row in source.get('cart_items', []):
            owner = row['owner']
            if owner.startswith('u:'):
                owner = 'u:' + legacy_id('users', owner[2:])
            db.execute('INSERT OR IGNORE INTO carts(owner) VALUES(?)', (owner,))
            cid = db.execute('SELECT id FROM carts WHERE owner=?', (owner,)).fetchone()[0]
            pid = legacy_id('products', row['product_id'])
            price = db.execute('SELECT price FROM products WHERE id=?', (pid,)).fetchone()[0]
            db.execute('INSERT INTO cart_items(cart_id,product_id,quantity,unit_price) VALUES(?,?,?,?)', (cid, pid, row['quantity'], price))
        for row in source.get('products', []):
            pid = legacy_id('products', row['id'])
            db.execute('INSERT INTO product_image(product_id,image_url,is_primary) VALUES(?,?,1)', (pid, row['image']))
            attrs = json.loads(row['attributes'])
            if row['category_id'] == 1:
                db.execute('INSERT INTO pen VALUES(?,?,?)', (pid, attrs.get('màu'), attrs.get('type', 'Bút viết')))
            elif row['category_id'] == 2:
                db.execute('INSERT INTO notebook VALUES(?,?,?,?)', (pid, int(attrs.get('trang', 1)), attrs.get('khổ', 'Khác'), attrs.get('type', 'Sổ / vở')))
        for order in source.get('orders', []):
            if order['status'] in ('pending', 'confirmed', 'picking', 'packed'):
                for item in source['order_items']:
                    if item['order_id'] == order['id']:
                        db.execute('INSERT INTO inventory_reservations VALUES(?,?,?)', (legacy_id('orders', order['id']), legacy_id('products', item['product_id']), item['quantity']))
        db.execute('UPDATE products SET average_rating=COALESCE((SELECT AVG(rating) FROM reviews WHERE product_id=products.id),0)')
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise RuntimeError('Migration failed foreign key validation')
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.execute('PRAGMA foreign_keys=ON')


def upgrade(db, path, schema):
    exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
    if not exists:
        db.executescript(schema)
        return
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version > 3:
        raise RuntimeError('Database version is newer than this application')
    if version < 2:
        _upgrade_v1(db, path, Path(__file__).with_name('schema_v2.sql').read_text(encoding='utf-8'))
        version = 2
    if version == 2:
        _upgrade_v2(db, path, schema)
    else:
        db.executescript(schema)


def _upgrade_v2(db, path, schema):
    backup = Path(str(path) + '.pre-design-v3.sqlite')
    if backup.exists():
        raise RuntimeError(f'Backup already exists: {backup}. Check the previous migration before retrying.')
    with sqlite3.connect(backup) as target:
        db.backup(target)
    if db.execute('PRAGMA foreign_key_check').fetchall():
        raise RuntimeError('Migration failed foreign key validation')
    db.execute('PRAGMA foreign_keys=OFF')
    try:
        db.execute('BEGIN IMMEDIATE')
        db.execute('CREATE TABLE migration_archive(name TEXT PRIMARY KEY,data TEXT NOT NULL)')
        categories = [dict(r) for r in db.execute('SELECT * FROM categories')]
        assignments = [dict(r) for r in db.execute('SELECT id,category_id,product_type,status FROM products')]
        db.execute('INSERT INTO migration_archive VALUES(?,?)', ('v2.categories',json.dumps(categories,ensure_ascii=False)))
        db.execute('INSERT INTO migration_archive VALUES(?,?)', ('v2.product_categories',json.dumps(assignments,ensure_ascii=False)))
        # Preserve products outside the six specializations without inventing a type.
        db.execute("UPDATE products SET status='ARCHIVED' WHERE product_type IS NULL")
        db.execute('ALTER TABLE products DROP COLUMN category_id')
        db.execute('DROP TABLE categories')
        # Execute statements individually: executescript would commit this migration early.
        statement = ''
        for line in schema.splitlines(keepends=True):
            statement += line
            if sqlite3.complete_statement(statement):
                if statement.strip() and not statement.strip().startswith('PRAGMA foreign_keys'):
                    db.execute(statement)
                statement = ''
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise RuntimeError('Migration failed foreign key validation')
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.execute('PRAGMA foreign_keys=ON')
