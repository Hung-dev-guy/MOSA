"""Upsert the collected ADCBook sample into SQL Server staging."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.infrastructure.database import SqlServerConnectionFactory


DEFAULT_DATASET = Path("datasets/adcbook_stationery/products.jsonl")


def first(values: list[str] | None) -> str:
    return (values or [""])[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--exclude-source-ids", nargs="*", default=[])
    args = parser.parse_args()
    excluded = set(args.exclude_source_ids)
    rows = [
        row
        for line in args.dataset.read_text(encoding="utf-8").splitlines()
        if line
        for row in [json.loads(line)]
        if str(row.get("source_id")) not in excluded
    ]
    factory = SqlServerConnectionFactory()
    update_sql = """
        UPDATE dbo.ExternalProductStaging
        SET SourceUrl=?, NameVi=?, Brand=?, ProductType=?, Category=?, Color=?, ColorVi=?,
            Price=?, IsAvailable=?, DescriptionVi=?, ImageUrl=?, LocalImagePath=?,
            ImageRightsNote=?, SourceJson=?, ScrapedAt=?, ImportedAt=SYSUTCDATETIME()
        WHERE SourceName=? AND SourceProductId=?
    """
    insert_sql = """
        INSERT INTO dbo.ExternalProductStaging
            (SourceName, SourceProductId, SourceUrl, NameVi, Brand, ProductType,
             Category, Color, ColorVi, Price, IsAvailable, DescriptionVi, ImageUrl,
             LocalImagePath, ImageRightsNote, SourceJson, ScrapedAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    with factory.connect() as connection:
        cursor = connection.cursor()
        inserted = 0
        updated = 0
        for row in rows:
            source_name = row["source"]
            source_id = str(row["source_id"])
            scraped_at = datetime.fromisoformat(row["scraped_at_utc"].replace("Z", "+00:00")).replace(tzinfo=None)
            source_json = json.dumps(row, ensure_ascii=False)
            values = (
                row["source_url"],
                row["name_vi"],
                row["brand"],
                row["product_type"],
                row["category"],
                row["color"],
                row["color_vi"],
                row["price_vnd"],
                row["available"],
                row["description_vi"],
                first(row["image_urls"]),
                first(row["local_images"]),
                row["image_rights_note"],
                source_json,
                scraped_at,
                source_name,
                source_id,
            )
            cursor.execute(update_sql, values)
            if cursor.rowcount:
                updated += 1
                continue
            cursor.execute(
                insert_sql,
                source_name,
                source_id,
                row["source_url"],
                row["name_vi"],
                row["brand"],
                row["product_type"],
                row["category"],
                row["color"],
                row["color_vi"],
                row["price_vnd"],
                row["available"],
                row["description_vi"],
                first(row["image_urls"]),
                first(row["local_images"]),
                row["image_rights_note"],
                source_json,
                scraped_at,
            )
            inserted += 1
        connection.commit()
    print(f"ExternalProductStaging: inserted={inserted}, updated={updated}, total={len(rows)}")


if __name__ == "__main__":
    main()

