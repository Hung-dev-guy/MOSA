"""Promote the reviewed ADCBook staging records into the live MOSA catalog."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.infrastructure.database import SqlServerConnectionFactory


DEFAULT_DATASET = PROJECT_ROOT / "datasets/adcbook_stationery/products.jsonl"
PUBLIC_IMAGES = PROJECT_ROOT / "static/images/catalog/adcbook"


def code_for(source_id: int | str) -> str:
    return f"A{str(source_id)[-9:]}"


def truncate_nvarchar(value: str, max_units: int) -> str:
    """Trim by SQL Server NVARCHAR UTF-16 code units, not Python code points."""
    result: list[str] = []
    used = 0
    for character in value:
        units = len(character.encode("utf-16-le")) // 2
        if used + units > max_units:
            break
        result.append(character)
        used += units
    return "".join(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--exclude-source-ids", nargs="*", default=[])
    args = parser.parse_args()
    dataset = args.dataset.resolve()
    excluded = set(args.exclude_source_ids)
    rows = [
        row
        for line in dataset.read_text(encoding="utf-8").splitlines()
        if line
        for row in [json.loads(line)]
        if str(row.get("source_id")) not in excluded
    ]
    PUBLIC_IMAGES.mkdir(parents=True, exist_ok=True)

    factory = SqlServerConnectionFactory()
    with factory.connect() as connection:
        cursor = connection.cursor()
        next_id = cursor.execute("SELECT ISNULL(MAX(ProductId), 0) + 1 FROM dbo.Products").fetchval()
        inserted = 0
        updated = 0

        for row in rows:
            local_images = row.get("local_images") or []
            image_path = ""
            if local_images:
                source = dataset.parent / local_images[0]
                destination = PUBLIC_IMAGES / source.name
                shutil.copy2(source, destination)
                image_path = f"images/catalog/adcbook/{destination.name}"

            product_code = code_for(row["source_id"])
            existing_id = cursor.execute(
                "SELECT ProductId FROM dbo.Products WHERE ProductCode = ?", product_code
            ).fetchval()
            description = truncate_nvarchar(row.get("description_vi") or "", 500)
            name = truncate_nvarchar(row["name_vi"], 200)
            values = (
                name,
                name,
                truncate_nvarchar(row.get("brand") or "ADCBook", 100),
                row["category"],
                row.get("color") or "multicolor",
                row.get("price_vnd") or 0,
                1 if row.get("available") else 0,
                description,
                description,
                image_path,
            )
            if existing_id is not None:
                cursor.execute(
                    """
                    UPDATE dbo.Products
                    SET Name=?, NameVi=?, Brand=?, Category=?, Color=?, Price=?, Stock=?,
                        Description=?, DescriptionVi=?, ImagePath=?, IsActive=1,
                        UpdatedAt=SYSUTCDATETIME()
                    WHERE ProductId=?
                    """,
                    *values,
                    existing_id,
                )
                updated += 1
            else:
                cursor.execute(
                    """
                    INSERT INTO dbo.Products
                        (ProductId, ProductCode, Name, NameVi, Brand, Category, Color,
                         Price, Stock, Description, DescriptionVi, ImagePath, IsActive, UpdatedAt)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, SYSUTCDATETIME())
                    """,
                    next_id,
                    product_code,
                    *values,
                )
                next_id += 1
                inserted += 1

        connection.commit()
    print(f"Products: inserted={inserted}, updated={updated}, promoted={len(rows)}")
    print(f"Images: {PUBLIC_IMAGES}")


if __name__ == "__main__":
    main()

