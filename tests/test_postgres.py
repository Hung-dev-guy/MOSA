"""Run against a disposable schema, never the imported public tables.

Set POSTGRES_TEST_URL and standard PGUSER/PGPASSWORD to enable integration tests.
"""
import inspect
import os
from urllib.parse import urlencode, quote
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from backend.app import create_app
from backend.data_infrastructure.database.connection import get_db
from backend.data_infrastructure.database.postgres import parameters
import test_cart
import test_orders
import test_operations
import test_reports_reviews
import test_identity
import test_discovery
import test_design_alignment
import test_admin_products


def test_parameter_translation_preserves_literals():
    assert parameters("SELECT '?' AS literal, ? AS value, '100%' AS percent") == "SELECT '?' AS literal, %s AS value, '100%%' AS percent"


@pytest.fixture
def pg_app(tmp_path):
    url = os.environ.get('POSTGRES_TEST_URL')
    if not url:
        pytest.skip('POSTGRES_TEST_URL is not set')
    schema = 'mosa_test_' + uuid4().hex
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        try:
            separator = '&' if '?' in url else '?'
            app = create_app({'TESTING': True, 'DATABASE': url + separator + urlencode({'options': '-c search_path=' + schema}, quote_via=quote),
                              'SECRET_KEY': 'postgres-tests', 'QUERY_MEDIA_DIRECTORY': str(tmp_path/'media')})
            yield app
        finally:
            admin.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


CASES = [function for module in (test_cart, test_orders, test_operations, test_reports_reviews, test_identity, test_discovery, test_admin_products)
         for name, function in vars(module).items()
         if name.startswith('test_') and callable(function)]


@pytest.mark.parametrize('case', CASES, ids=lambda fn: fn.__name__)
def test_customer_and_operations_on_postgres(pg_app, case):
    available = {'app': pg_app, 'client': pg_app.test_client()}
    case(**{key: available[key] for key in inspect.signature(case).parameters})


def test_postgres_rollback_numeric_and_literal_safety(pg_app):
    with pg_app.app_context():
        db = get_db()
        value = "Đỗ Thiện Minh's ? 100% \\ ảnh"
        row = db.execute("SELECT ? AS text, '?' AS question, '100%' AS percent", (value,)).fetchone()
        assert tuple(row) == (value, '?', '100%')
        assert dict(row)['text'] == value
        db.execute('UPDATE products SET stock=stock+1')
        db.rollback()
        assert db.execute('SELECT stock FROM products ORDER BY rowid LIMIT 1').fetchone()[0] == 90
        reserved = db.execute('SELECT COALESCE(SUM(quantity),0) AS quantity FROM inventory_reservations').fetchone()
        assert isinstance(reserved['quantity'], int)


@pytest.mark.parametrize('kind', test_design_alignment.DETAILS)
def test_postgres_product_subtypes(pg_app, kind):
    test_design_alignment.test_subtype_shared_identity_validation_and_filters(pg_app, pg_app.test_client(), kind)
