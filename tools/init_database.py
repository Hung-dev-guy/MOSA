"""Create and seed the Docker SQL Server database.

The SQL files are idempotent. Existing Docker volumes keep their data, while a
fresh volume receives the catalog exported from the development database.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

import pyodbc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_DIRECTORY = PROJECT_ROOT / "database" / "docker"
DATABASE_TOKEN = "__MOSA_DATABASE__"


def odbc_value(value: str) -> str:
    return "{" + value.replace("}", "}}") + "}"


def connection_string(database: str) -> str:
    driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    server = os.getenv("DB_SERVER", "db,1433")
    user = os.getenv("DB_USER", "sa").strip()
    password = os.getenv("DB_PASSWORD", "")
    encrypt = os.getenv("DB_ENCRYPT", "yes")
    auth = (
        f"UID={odbc_value(user)};PWD={odbc_value(password)};"
        if user
        else "Trusted_Connection=yes;"
    )
    return (
        f"DRIVER={{{driver}}};SERVER={odbc_value(server)};"
        f"DATABASE={odbc_value(database)};{auth}Encrypt={encrypt};"
        "TrustServerCertificate=yes;"
    )


def wait_for_server() -> pyodbc.Connection:
    last_error: Exception | None = None
    for attempt in range(1, 61):
        try:
            return pyodbc.connect(
                connection_string("master"), timeout=5, autocommit=True
            )
        except pyodbc.Error as error:
            last_error = error
            print(f"SQL Server chưa sẵn sàng ({attempt}/60); thử lại sau 2 giây.")
            time.sleep(2)
    raise RuntimeError("Không thể kết nối SQL Server sau 120 giây.") from last_error


def batches(sql: str) -> list[str]:
    return [
        value.strip()
        for value in re.split(r"^\s*GO\s*(?:--.*)?$", sql, flags=re.IGNORECASE | re.MULTILINE)
        if value.strip()
    ]


def run_script(connection: pyodbc.Connection, path: Path) -> None:
    print(f"Đang chạy {path.name}...")
    database = os.getenv("DB_NAME", "ECommerceMultimodalV1")
    safe_identifier = database.replace("]", "]]" )
    safe_literal = database.replace("'", "''")
    sql = path.read_text(encoding="utf-8-sig")
    sql = sql.replace(f"[{DATABASE_TOKEN}]", f"[{safe_identifier}]")
    sql = sql.replace(f"N'{DATABASE_TOKEN}'", f"N'{safe_literal}'")
    for batch in batches(sql):
        connection.cursor().execute(batch)


def main() -> None:
    scripts = [SQL_DIRECTORY / "001_schema.sql", SQL_DIRECTORY / "002_seed_data.sql"]
    missing = [str(path) for path in scripts if not path.exists()]
    if missing:
        raise FileNotFoundError("Thiếu SQL khởi tạo: " + ", ".join(missing))

    connection = wait_for_server()
    try:
        for path in scripts:
            run_script(connection, path)
    finally:
        connection.close()

    database = os.getenv("DB_NAME", "ECommerceMultimodalV1")
    with pyodbc.connect(connection_string(database), timeout=10) as check:
        cursor = check.cursor()
        products = cursor.execute("SELECT COUNT(*) FROM dbo.Products").fetchval()
        active = cursor.execute(
            "SELECT COUNT(*) FROM dbo.Products WHERE IsActive = 1"
        ).fetchval()
        staging = cursor.execute(
            "SELECT COUNT(*) FROM dbo.ExternalProductStaging"
        ).fetchval()
    print(
        f"Database đã sẵn sàng: Products={products}, "
        f"Active={active}, Staging={staging}."
    )


if __name__ == "__main__":
    main()
