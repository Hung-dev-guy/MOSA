import json
from decimal import Decimal

from src.domain.models import Product
from src.infrastructure.database import SqlServerConnectionFactory


class ProductRepository:
    def __init__(self, connection_factory: SqlServerConnectionFactory) -> None:
        self.connection_factory = connection_factory

    def list_active(self, category: str = "") -> list[Product]:
        sql = """
            SELECT ProductId, ProductCode, Name, NameVi, Brand, Category, Color,
                   Price, Stock, Description, DescriptionVi, ImagePath
            FROM dbo.Products
            WHERE IsActive = 1
        """
        params: list[str] = []
        if category:
            sql += " AND Category = ?"
            params.append(category)
        sql += " ORDER BY CASE WHEN Stock > 0 THEN 0 ELSE 1 END, ProductId"

        with self.connection_factory.connect() as connection:
            rows = connection.cursor().execute(sql, params).fetchall()

        return [
            Product(
                product_id=row.ProductId,
                product_code=row.ProductCode,
                name=row.Name,
                name_vi=row.NameVi,
                brand=row.Brand,
                category=row.Category,
                color=row.Color,
                price=Decimal(row.Price),
                stock=row.Stock,
                description=row.Description,
                description_vi=row.DescriptionVi,
                image_path=row.ImagePath,
            )
            for row in rows
        ]

    def categories(self) -> list[dict]:
        sql = """
            SELECT Category, COUNT(*) AS ProductCount
            FROM dbo.Products
            WHERE IsActive = 1
            GROUP BY Category
            ORDER BY COUNT(*) DESC, Category
        """
        with self.connection_factory.connect() as connection:
            rows = connection.cursor().execute(sql).fetchall()
        return [{"name": row.Category, "count": row.ProductCount} for row in rows]

    def log_search(
        self,
        mode: str,
        input_text: str,
        results: list[dict],
        duration_ms: float,
    ) -> None:
        sql = """
            INSERT INTO dbo.SearchEvents
                (SearchMode, InputText, CandidateCount, ResultJson, DurationMs, CreatedAt)
            VALUES (?, ?, ?, ?, ?, SYSUTCDATETIME())
        """
        compact_results = [
            {"product_id": item["product_id"], "score": item["score"]}
            for item in results[:12]
        ]
        with self.connection_factory.connect() as connection:
            connection.cursor().execute(
                sql,
                mode[:20],
                input_text[:2000],
                len(results),
                json.dumps(compact_results, ensure_ascii=False),
                round(duration_ms, 2),
            )
            connection.commit()

