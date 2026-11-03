import io
import re
import time
import unicodedata
from collections import Counter

from PIL import Image, ImageOps

from src.domain.models import Product, SearchRequest
from src.infrastructure.product_repository import ProductRepository


def normalize(value: str | None) -> str:
    value = value or ""
    decomposed = unicodedata.normalize("NFD", value.lower())
    without_accents = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", without_accents).strip()


class DominantColorImageEncoder:
    """Lightweight local image encoder; replaceable by a CLIP/vector adapter."""

    COLOR_CENTERS = {
        "black": (28, 28, 30),
        "white": (235, 235, 232),
        "grey": (130, 132, 136),
        "red": (190, 55, 55),
        "green": (55, 145, 85),
        "blue": (55, 100, 180),
        "brown": (125, 82, 52),
        "yellow": (220, 185, 55),
    }

    def encode(self, image_bytes: bytes) -> dict:
        with Image.open(io.BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((96, 96))
            pixels = list(image.getdata())

        visible = [pixel for pixel in pixels if max(pixel) - min(pixel) > 8 or sum(pixel) < 720]
        sample = visible or pixels
        average = tuple(sum(pixel[i] for pixel in sample) / len(sample) for i in range(3))
        color = min(
            self.COLOR_CENTERS,
            key=lambda name: sum(
                (average[i] - self.COLOR_CENTERS[name][i]) ** 2 for i in range(3)
            ),
        )
        return {"color": color, "rgb": [round(channel) for channel in average]}


class RankingService:
    def rank(self, products: list[Product], request: SearchRequest) -> list[dict]:
        query = normalize(request.query)
        tokens = Counter(token for token in query.split() if len(token) > 1)
        ranked: list[dict] = []

        for product in products:
            primary = normalize(" ".join(filter(None, [product.name_vi, product.name])))
            searchable = normalize(
                " ".join(
                    filter(
                        None,
                        [
                            product.name,
                            product.name_vi,
                            product.brand,
                            product.category,
                            product.color,
                            product.description,
                            product.description_vi,
                        ],
                    )
                )
            )
            score = 0.0
            reasons: list[str] = []
            matched = not query and not request.color_hint
            searchable_tokens = set(searchable.split())

            if query:
                if query in primary:
                    score += 65
                    matched = True
                    reasons.append("Tên sản phẩm khớp cụm từ")
                elif query in searchable:
                    score += 40
                    matched = True
                    reasons.append("Mô tả khớp cụm từ")

                hits = sum(weight for token, weight in tokens.items() if token in searchable_tokens)
                if hits:
                    score += min(42, hits * 14)
                    matched = True
                    reasons.append(f"Khớp {hits} từ khóa")

            if request.color_hint and normalize(product.color) == normalize(request.color_hint):
                score += 72
                matched = True
                reasons.append(f"Màu chủ đạo: {request.color_hint}")

            if product.stock > 0:
                score += 4
            elif query or request.color_hint:
                score -= 20

            if not query and not request.color_hint:
                score += 10

            if matched and score > 0:
                ranked.append(product.to_dict(score, reasons))

        ranked.sort(key=lambda item: (-item["score"], -item["stock"], item["price"]))
        return ranked[: request.limit]


class SearchOrchestrator:
    VALID_MODES = {"text", "voice", "image"}

    def __init__(
        self,
        repository: ProductRepository,
        ranking_service: RankingService,
        image_encoder: DominantColorImageEncoder,
    ) -> None:
        self.repository = repository
        self.ranking_service = ranking_service
        self.image_encoder = image_encoder

    def search(self, request: SearchRequest) -> dict:
        if request.mode not in self.VALID_MODES:
            raise ValueError("Chế độ tìm kiếm không hợp lệ.")

        started = time.perf_counter()
        products = self.repository.list_active(request.category)
        results = self.ranking_service.rank(products, request)
        duration_ms = (time.perf_counter() - started) * 1000
        event_text = request.query or (f"image-color:{request.color_hint}" if request.color_hint else "")
        self.repository.log_search(request.mode, event_text, results, duration_ms)
        return {
            "mode": request.mode,
            "query": request.query,
            "color_hint": request.color_hint,
            "count": len(results),
            "duration_ms": round(duration_ms, 2),
            "results": results,
        }

    def search_image(
        self,
        image_bytes: bytes,
        query: str = "",
        category: str = "",
    ) -> dict:
        feature = self.image_encoder.encode(image_bytes)
        response = self.search(
            SearchRequest(
                mode="image",
                query=query,
                category=category,
                color_hint=feature["color"],
            )
        )
        response["image_feature"] = feature
        return response

