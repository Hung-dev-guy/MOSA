import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import g, current_app
from werkzeug.security import generate_password_hash


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def connect(path):
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db


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
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = connect(path)
    db.executescript(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))
    if not db.execute('SELECT 1 FROM categories').fetchone():
        names = ['Bút viết', 'Sổ & tập vở', 'Giấy in', 'Dụng cụ học tập', 'Hồ sơ văn phòng', 'Màu & mỹ thuật']
        db.executemany('INSERT INTO categories(name) VALUES(?)', [(n,) for n in names])
        catalogue = [
            (1,'Bút gel Thiên Long FlexOffice 0.5mm', 'Thiên Long',12000,'Cây',1, {'màu':'xanh','ngòi':'0.5mm'},'pen-blue',90),
            (2,'Sổ tay lò xo Pastel A5 120 trang','Mosa',45000,'Quyển',1,{'khổ':'A5','trang':'120'},'notebook',55),
            (3,'Giấy in Double A A4 80gsm','Double A',89000,'Ram',500,{'khổ':'A4','định lượng':'80gsm'},'paper',80),
            (4,'Bộ thước học sinh 4 món','Deli',25000,'Bộ',4,{'màu':'xanh'},'ruler',65),
            (5,'Bìa còng văn phòng A4 7cm','Deli',58000,'Chiếc',1,{'khổ':'A4','màu':'xanh'},'folder',40),
            (6,'Bút chì màu Colokit 24 màu','Thiên Long',69000,'Hộp',24,{'màu':'24 màu'},'colors',35),
            (1,'Hộp 12 bút gel xanh 0.5mm','Thiên Long',125000,'Hộp',12,{'màu':'xanh','ngòi':'0.5mm'},'pen-box',20),
            (2,'Tập học sinh 96 trang ô ly','Hồng Hà',15000,'Quyển',1,{'trang':'96','khổ':'B5'},'exercise',120),
            (4,'Kéo thủ công an toàn 135mm','Deli',22000,'Chiếc',1,{'màu':'hồng'},'scissors',28),
            (4,'Băng keo giấy trang trí Pastel','Mosa',18000,'Cuộn',1,{'màu':'hồng'},'tape',45),
            (5,'Kẹp giấy màu hộp 50 chiếc','Deli',16000,'Hộp',50,{'màu':'nhiều màu'},'clips',70),
            (6,'Màu nước sáng tạo 12 màu','Colokit',72000,'Hộp',12,{'màu':'12 màu'},'paint',30),
        ]
        for cat,name,brand,price,unit,pack,attrs,image,stock in catalogue:
            db.execute('INSERT INTO products(category_id,name,description,brand,price,selling_unit,pack_quantity,attributes,image,published,stock) VALUES(?,?,?,?,?,?,?,?,?,1,?)',
                       (cat,name,f'{name}. Dụng cụ chất lượng cho học tập và công việc. Kiểm tra đơn vị bán và thông số trước khi chọn mua.',brand,price,unit,pack,json.dumps(attrs,ensure_ascii=False),f'/assets/{image}.png',stock))
        db.execute("INSERT INTO promotions(code,percent,minimum,starts_at,ends_at) VALUES('MOSA10',10,50000,'2020-01-01T00:00:00+00:00','2035-12-31T23:59:59+00:00')")
    if demo and not db.execute('SELECT 1 FROM users').fetchone():
        password = generate_password_hash('Mosa@12345')
        for role in ['customer','admin','warehouse','sales','manager']:
            db.execute('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)',(f'Mosa {role}',f'{role}@mosa.local',password,role))
    db.commit()
    db.close()
