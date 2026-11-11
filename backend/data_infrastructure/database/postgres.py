"""Keep the existing service SQL/transaction contract when using PostgreSQL."""
from decimal import Decimal
import re

import psycopg
from psycopg.pq import TransactionStatus


class Row:
    """sqlite3.Row-compatible name/index access, including dict(row)."""
    def __init__(self, values):
        self.data = dict(values)

    def __getitem__(self, key):
        return tuple(self.data.values())[key] if isinstance(key, int) else self.data[key]

    def keys(self):
        return self.data.keys()

    def __iter__(self):
        return iter(self.data.values())

    def __len__(self):
        return len(self.data)


def row_factory(cursor):
    columns = [column.name for column in cursor.description or ()]

    def make_row(values):
        # PostgreSQL SUM(bigint) returns Decimal; preserve JSON numeric fields.
        return Row((key, int(value) if value == value.to_integral_value() else float(value))
                   if isinstance(value, Decimal) else (key, value)
                   for key, value in zip(columns, values) if key != 'rowid')
    return make_row


def parameters(sql):
    # Only replace placeholders outside SQL string/identifier literals.
    return re.sub(r"'([^']|'')*'|\"([^\"]|\"\")*\"|\?",
                  lambda match: '%s' if match[0] == '?' else match[0],
                  sql.replace('%', '%%'))


class PostgresConnection:
    def __init__(self, url):
        self.raw = psycopg.connect(url, autocommit=True, row_factory=row_factory,
                                   connect_timeout=15)

    def begin_write(self):
        if self.raw.info.transaction_status == TransactionStatus.IDLE:
            self.raw.execute('BEGIN')
            # shortcut: serialize writes like SQLite; use per-record locks if write traffic grows.
            self.raw.execute('SELECT pg_advisory_xact_lock(1297044289)')

    def execute(self, sql, args=()):
        if sql.strip().upper() == 'BEGIN IMMEDIATE':
            self.begin_write()
            return self.raw.cursor()
        if re.match(r'\s*(INSERT|UPDATE|DELETE)\b', sql, re.I):
            self.begin_write()
        return self.raw.execute(parameters(sql), args)

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()

    def close(self):
        self.raw.close()
