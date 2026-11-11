"""Export a read-only SQLite snapshot for psql; import only into empty tables."""
import argparse
import math
from pathlib import Path
import re
import sqlite3


def identifier(value):
    return '"' + value.replace('"', '""') + '"'


def literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and math.isfinite(value):
        return repr(value)
    if isinstance(value, str) and "\x00" not in value:
        return "'" + value.replace("'", "''") + "'"
    raise ValueError("Unsupported SQLite value (binary, NUL, or non-finite number)")


def export(source, destination):
    schema = Path(__file__).resolve().parents[1] / "backend/data_infrastructure/database/schema_postgres.sql"
    expected = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)\(", schema.read_text(encoding="utf-8")))
    with sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True) as db:
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("SQLite integrity check failed")
        if db.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("SQLite contains broken foreign keys")
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        if tables != expected:
            raise ValueError(f"Schema differs: missing={expected - tables}, extra={tables - expected}")
        dependencies = {
            t: {r[2] for r in db.execute(f"PRAGMA foreign_key_list({identifier(t)})")} - {t}
            for t in tables
        }
        ordered = []
        while dependencies:
            ready = sorted(t for t, parents in dependencies.items() if not parents)
            if not ready:
                raise ValueError("Circular foreign keys cannot be exported")
            ordered.extend(ready)
            for t in ready:
                del dependencies[t]
            for parents in dependencies.values():
                parents.difference_update(ready)
        counts = {}
        statements = ["BEGIN;", "SET LOCAL standard_conforming_strings = on;"]
        for t in ordered:
            name = identifier(t)
            # Block concurrent writes between the emptiness check and inserts.
            statements.append(f"LOCK TABLE {name} IN EXCLUSIVE MODE;")
            statements.append(f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM {name}) THEN RAISE EXCEPTION 'Target table is not empty: {t}'; END IF; END $$;")
            # Preserve snapshot metadata; FK and CHECK constraints stay enabled.
            statements.append(f"ALTER TABLE {name} DISABLE TRIGGER USER;")
        for t in ordered:
            cursor = db.execute(f"SELECT * FROM {identifier(t)}")
            columns = ",".join(identifier(c[0]) for c in cursor.description)
            counts[t] = 0
            for row in cursor:
                statements.append(f"INSERT INTO {identifier(t)} ({columns}) VALUES ({','.join(literal(v) for v in row)});")
                counts[t] += 1
        for t in ordered:
            name = identifier(t)
            statements.append(f"ALTER TABLE {name} ENABLE TRIGGER USER;")
            statements.append(f"DO $$ BEGIN IF (SELECT count(*) FROM {name}) <> {counts[t]} THEN RAISE EXCEPTION 'Count mismatch: {t}'; END IF; END $$;")
        statements.append("DO $$ BEGIN IF EXISTS (SELECT 1 FROM products p JOIN inventory_reservations r ON r.product_id=p.id GROUP BY p.id,p.stock HAVING sum(r.quantity)>p.stock) THEN RAISE EXCEPTION 'Reservations exceed stock'; END IF; END $$;")
        for subtype in ("pen", "notebook", "bag", "toy", "book", "electric_device"):
            statements.append(f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM {identifier(subtype)} s JOIN products p ON p.id=s.product_id WHERE p.product_type IS DISTINCT FROM '{subtype}') THEN RAISE EXCEPTION 'Product subtype mismatch: {subtype}'; END IF; END $$;")
        statements.append("COMMIT;")
        # Exclusive creation prevents accidentally overwriting a previous export.
        with destination.open("x", encoding="utf-8", newline="\n") as output:
            output.write("\n".join(statements) + "\n")
    for table, count in counts.items():
        print(f"{table}: {count}")
    print(f"Exported {len(counts)} tables, {sum(counts.values())} rows to {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    export(args.source, args.destination)
