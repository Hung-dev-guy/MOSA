import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .migrations import upgrade, legacy_id

from flask import g, current_app
from werkzeug.security import generate_password_hash


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def connect(path):
    if is_postgres(path):
        from .postgres import PostgresConnection
        return PostgresConnection(str(path))
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.create_function('uuid', 0, lambda: str(uuid4()))
    db.execute('PRAGMA foreign_keys=ON')
    return db


def is_postgres(path):
    return str(path).startswith(('postgresql://', 'postgres://'))


def get_db():
    if 'db' not in g:
        g.db = connect(current_app.config['DATABASE'])
    return g.db


def rows(sql, args=()):
    return [dict(r) for r in get_db().execute(sql, args).fetchall()]


def one(sql, args=()):
    r = get_db().execute(sql, args).fetchone()
    return dict(r) if r else None


def init_db(path, demo=True):
    if not is_postgres(path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = connect(path)
    try:
        if is_postgres(path):
            db.begin_write()
            schema = Path(__file__).with_name('schema_postgres.sql').read_text(encoding='utf-8')
            db.raw.execute(schema.replace('\nBEGIN;\n', '\n').removesuffix('COMMIT;\n'), prepare=False)
        else:
            upgrade(db, path, Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))
        seed(db, demo)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def seed(db, demo):
    if not db.execute('SELECT 1 FROM products').fetchone():
        catalogue = [
            ('pen','Bút gel Thiên Long FlexOffice 0.5mm','Thiên Long',12000,'Cây',1,{'ngòi':'0.5mm'},'pen-blue.png',90,{'color':'xanh','type':'Gel'}),
            ('notebook','Sổ tay lò xo Pastel A5 120 trang','Mosa',45000,'Quyển',1,{},'notebook.png',55,{'page_num':120,'size':'A5','type':'Lò xo'}),
            ('book','Sách khám phá khoa học','Kim Đồng',89000,'Cuốn',1,{},'book.png',80,{'category':'Khoa học','minimum_age':6,'publisher':'Kim Đồng'}),
            ('bag','Túi đựng dụng cụ học tập','Deli',25000,'Chiếc',1,{},'bag.png',65,{'size':'25 x 15 cm','pattern':'Trơn'}),
            ('toy','Bộ xếp hình sáng tạo','Deli',58000,'Bộ',1,{},'toy.png',40,{'type':'Xếp hình','minimum_age':6}),
            ('pen','Bút chì màu Colokit 24 màu','Thiên Long',69000,'Hộp',24,{},'colors.png',35,{'color':'24 màu','type':'Bút chì màu'}),
            ('pen','Hộp 12 bút gel xanh 0.5mm','Thiên Long',125000,'Hộp',12,{'ngòi':'0.5mm'},'pen-box.png',20,{'color':'xanh','type':'Gel'}),
            ('notebook','Tập học sinh 96 trang ô ly','Hồng Hà',15000,'Quyển',1,{},'exercise.png',120,{'page_num':96,'size':'B5','type':'Ô ly'}),
            ('book','Sách tô màu sáng tạo','Kim Đồng',22000,'Cuốn',1,{},'book.png',28,{'category':'Mỹ thuật','minimum_age':3,'publisher':'Kim Đồng'}),
            ('bag','Túi đeo chéo Pastel','Mosa',18000,'Chiếc',1,{},'bag.png',45,{'size':'20 x 15 cm','pattern':'Pastel'}),
            ('toy','Bộ ghép hình 50 miếng','Deli',16000,'Bộ',1,{},'toy.png',70,{'type':'Ghép hình','minimum_age':5}),
            ('electric_device','Đèn bàn học LED','Deli',72000,'Chiếc',1,{},'electric-device.png',30,{'minimum_age':None,'weight':300}),
        ]
        for index,(kind,name,brand,price,unit,pack,attrs,image,stock,details) in enumerate(catalogue,1):
            attrs['pack_quantity'] = pack
            pid = legacy_id('products', index)
            db.execute("INSERT INTO products(id,name,description,brand,price,selling_unit,attributes,image,status,stock,product_type) VALUES(?,?,?,?,?,?,?,?,'ACTIVE',?,?)",
                       (pid,name,f'{name}. Kiểm tra đơn vị bán và thông số trước khi chọn mua.',brand,price,unit,json.dumps(attrs,ensure_ascii=False),f'/assets/{image}',stock,kind))
            db.execute('INSERT INTO product_image(product_id,image_url,is_primary) VALUES(?,?,1)', (pid,f'/assets/{image}'))
            db.execute('INSERT INTO '+kind+'(product_id,'+','.join(details)+') VALUES('+','.join('?' for _ in range(len(details)+1))+')',(pid,*details.values()))
    if demo and not db.execute('SELECT 1 FROM users').fetchone():
        password = generate_password_hash('Mosa@12345')
        for index,role in enumerate(['customer','admin','warehouse','sales','manager'],1):
            db.execute('INSERT INTO users(id,name,email,password,role) VALUES(?,?,?,?,?)',(legacy_id('users', index),f'Mosa {role}',f'{role}@mosa.local',password,role))
    db.execute("INSERT INTO carts(owner,customer_id) SELECT 'u:'||id,id FROM users WHERE 1=1 ON CONFLICT DO NOTHING")
