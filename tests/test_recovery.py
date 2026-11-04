import sqlite3
import pytest
from conftest import call
from test_orders import checkout
from backend.data_infrastructure.database.connection import connect
from scripts.backup import backup


def test_durability_backup_restore(app,client,tmp_path):
    oid=checkout(client,'cod').json['id']
    dest=tmp_path/'backup.sqlite'
    backup(app.config['DATABASE'],dest)
    with connect(dest) as db:
        assert db.execute('SELECT reserved FROM products WHERE id=1').fetchone()[0]==2
        assert db.execute('SELECT status FROM orders WHERE id=?',(oid,)).fetchone()[0]=='confirmed'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('UPDATE products SET stock=0 WHERE id=1')
    restored=tmp_path/'restored.sqlite'
    backup(dest,restored)
    with connect(restored) as db:
        assert db.execute('SELECT COUNT(*) FROM order_items').fetchone()[0]==1
    with pytest.raises(ValueError):
        backup(dest,restored)
