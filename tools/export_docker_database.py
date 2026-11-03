"""Export the portable Docker schema and demo catalog from local SQL Server.

Only application tables are exported. Search history and archive tables are
intentionally excluded from the shareable package.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.infrastructure.database import SqlServerConnectionFactory


OUTPUT_DIRECTORY = PROJECT_ROOT / "database" / "docker"
DATABASE_TOKEN = "__MOSA_DATABASE__"
TABLES = ["Products", "SearchEvents", "ExternalProductStaging"]
SEEDED_TABLES = ["Products", "ExternalProductStaging"]


def quote_identifier(value: str) -> str:
    return "[" + value.replace("]", "]]" ) + "]"


def sql_type(row) -> str:
    name = row.TypeName.lower()
    if name in {"varchar", "char", "varbinary", "binary"}:
        length = "max" if row.max_length == -1 else str(row.max_length)
        return f"{name}({length})"
    if name in {"nvarchar", "nchar"}:
        length = "max" if row.max_length == -1 else str(row.max_length // 2)
        return f"{name}({length})"
    if name in {"decimal", "numeric"}:
        return f"{name}({row.precision},{row.scale})"
    if name in {"datetime2", "datetimeoffset", "time"}:
        return f"{name}({row.scale})"
    return name


def sql_literal(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, Decimal)):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, bytes):
        return "0x" + value.hex()
    if isinstance(value, datetime):
        return "CONVERT(datetime2, N'" + value.isoformat(timespec="microseconds") + "', 126)"
    if isinstance(value, date):
        return "CONVERT(date, N'" + value.isoformat() + "', 126)"
    if isinstance(value, time):
        return "CONVERT(time, N'" + value.isoformat(timespec="microseconds") + "', 126)"
    return "N'" + str(value).replace("'", "''") + "'"


def schema_for(connection, table: str) -> str:
    columns = connection.cursor().execute(
        """
        SELECT column_info.name AS ColumnName,
               type_info.name AS TypeName,
               column_info.max_length,
               column_info.precision,
               column_info.scale,
               column_info.is_nullable,
               column_info.is_identity,
               default_info.name AS DefaultName,
               default_info.definition AS DefaultDefinition
        FROM sys.columns AS column_info
        JOIN sys.types AS type_info
          ON column_info.user_type_id = type_info.user_type_id
        LEFT JOIN sys.default_constraints AS default_info
          ON column_info.default_object_id = default_info.object_id
        WHERE column_info.object_id = OBJECT_ID(?)
        ORDER BY column_info.column_id
        """,
        f"dbo.{table}",
    ).fetchall()
    if not columns:
        raise RuntimeError(f"Không tìm thấy dbo.{table}")

    definitions: list[str] = []
    for column in columns:
        definition = f"        {quote_identifier(column.ColumnName)} {sql_type(column)}"
        if column.is_identity:
            definition += " IDENTITY(1,1)"
        definition += " NULL" if column.is_nullable else " NOT NULL"
        if column.DefaultDefinition:
            definition += (
                f" CONSTRAINT {quote_identifier(column.DefaultName)} "
                f"DEFAULT {column.DefaultDefinition}"
            )
        definitions.append(definition)

    constraints = connection.cursor().execute(
        """
        SELECT constraint_info.name AS ConstraintName,
               constraint_info.type AS ConstraintType,
               index_column.key_ordinal,
               column_info.name AS ColumnName
        FROM sys.key_constraints AS constraint_info
        JOIN sys.index_columns AS index_column
          ON constraint_info.parent_object_id = index_column.object_id
         AND constraint_info.unique_index_id = index_column.index_id
        JOIN sys.columns AS column_info
          ON index_column.object_id = column_info.object_id
         AND index_column.column_id = column_info.column_id
        WHERE constraint_info.parent_object_id = OBJECT_ID(?)
        ORDER BY constraint_info.name, index_column.key_ordinal
        """,
        f"dbo.{table}",
    ).fetchall()
    grouped: dict[tuple[str, str], list[str]] = {}
    for constraint in constraints:
        grouped.setdefault(
            (constraint.ConstraintName, constraint.ConstraintType), []
        ).append(constraint.ColumnName)
    for (name, kind), column_names in grouped.items():
        keyword = "PRIMARY KEY" if kind == "PK" else "UNIQUE"
        joined = ", ".join(quote_identifier(value) for value in column_names)
        definitions.append(
            f"        CONSTRAINT {quote_identifier(name)} {keyword} ({joined})"
        )

    body = ",\n".join(definitions)
    return (
        f"IF OBJECT_ID(N'dbo.{table}', N'U') IS NULL\n"
        "BEGIN\n"
        f"    CREATE TABLE dbo.{quote_identifier(table)}\n"
        "    (\n"
        f"{body}\n"
        "    );\n"
        "END;\nGO\n"
    )


def seed_for(connection, table: str) -> str:
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM dbo.{quote_identifier(table)} ORDER BY 1")
    columns = [column[0] for column in cursor.description]
    rows = cursor.fetchall()
    identity_count = connection.cursor().execute(
        """
        SELECT COUNT(*)
        FROM sys.columns
        WHERE object_id = OBJECT_ID(?) AND is_identity = 1
        """,
        f"dbo.{table}",
    ).fetchval()
    column_list = ", ".join(quote_identifier(value) for value in columns)
    result = [
        f"IF NOT EXISTS (SELECT 1 FROM dbo.{quote_identifier(table)})",
        "BEGIN",
    ]
    if identity_count:
        result.append(f"    SET IDENTITY_INSERT dbo.{quote_identifier(table)} ON;")
    for row in rows:
        values = ", ".join(sql_literal(value) for value in row)
        result.append(
            f"    INSERT INTO dbo.{quote_identifier(table)} ({column_list}) "
            f"VALUES ({values});"
        )
    if identity_count:
        result.append(f"    SET IDENTITY_INSERT dbo.{quote_identifier(table)} OFF;")
    result.extend(["END;", "GO", ""])
    print(f"dbo.{table}: {len(rows)} bản ghi")
    return "\n".join(result)


def main() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    factory = SqlServerConnectionFactory()
    with factory.connect() as connection:
        schema_parts = [
            f"IF DB_ID(N'{DATABASE_TOKEN}') IS NULL CREATE DATABASE [{DATABASE_TOKEN}];",
            "GO",
            f"USE [{DATABASE_TOKEN}];",
            "GO",
            "SET ANSI_NULLS ON;",
            "SET QUOTED_IDENTIFIER ON;",
            "GO",
            "",
        ]
        for table in TABLES:
            schema_parts.append(schema_for(connection, table))

        seed_parts = [
            f"USE [{DATABASE_TOKEN}];",
            "GO",
            "SET XACT_ABORT ON;",
            "BEGIN TRANSACTION;",
            "GO",
            "",
        ]
        for table in SEEDED_TABLES:
            seed_parts.append(seed_for(connection, table))
        seed_parts.extend(["COMMIT TRANSACTION;", "GO", ""])

    schema_path = OUTPUT_DIRECTORY / "001_schema.sql"
    seed_path = OUTPUT_DIRECTORY / "002_seed_data.sql"
    schema_path.write_text("\n".join(schema_parts), encoding="utf-8-sig")
    seed_path.write_text("\n".join(seed_parts), encoding="utf-8-sig")
    print(schema_path)
    print(seed_path)


if __name__ == "__main__":
    main()
