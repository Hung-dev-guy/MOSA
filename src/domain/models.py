from dataclasses import asdict, dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Product:
    product_id: int
    product_code: str
    name: str
    name_vi: str | None
    brand: str
    category: str
    color: str
    price: Decimal
    stock: int
    description: str | None
    description_vi: str | None
    image_path: str

    def to_dict(self, score: float = 0.0, reasons: list[str] | None = None) -> dict:
        data = asdict(self)
        data["price"] = float(self.price)
        data["score"] = round(score, 2)
        data["match_reasons"] = reasons or []
        return data


@dataclass(frozen=True)
class SearchRequest:
    mode: str
    query: str = ""
    category: str = ""
    color_hint: str = ""
    limit: int = 24

