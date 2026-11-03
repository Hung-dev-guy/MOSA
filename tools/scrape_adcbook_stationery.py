"""Collect a small, traceable Vietnamese stationery dataset from ADCBook.

The crawler only visits public collection/product JSON URLs allowed by the
site's robots.txt. It is intentionally rate-limited and keeps source/rights
metadata with every record.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


BASE_URL = "https://adcbook.net.vn"
DEFAULT_COLLECTIONS = [
    "/but-viet",
    "/vo-hoc-sinh",
    "/giay-note",
    "/so-cac-loai",
    "/dung-cu-hoc-sinh",
    "/van-phong-pham-tieu-hoc",
    "/van-phong-pham-trung-hoc-co-so",
    "/van-phong-pham-trung-hoc-pho-thong",
    "/van-phong-pham-doanh-nghiep",
    "/but-gel-but-nuoc-ruot-but-gel",
    "/but-bi-ruot-but-bi",
    "/so-bia-cung",
    "/so-bia-da",
    "/so-lo-xo",
]
USER_AGENT = "MOSA-Dataset-Builder/1.0 (local educational prototype)"
RIGHTS_NOTE = (
    "Ảnh sản phẩm từ ADCBook/Bizweb; chỉ dùng cho prototype nội bộ. "
    "Cần xin phép chủ sở hữu trước khi phân phối hoặc sử dụng thương mại."
)


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


def html_to_text(value: str | None) -> str:
    parser = TextExtractor()
    parser.feed(value or "")
    return html.unescape(" ".join(parser.parts)).strip()


def fetch(url: str, timeout: int = 30) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/html,application/xhtml+xml,image/*;q=0.8,*/*;q=0.5",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def check_robots(collection_paths: list[str]) -> None:
    robots_url = f"{BASE_URL}/robots.txt"
    parser = urllib.robotparser.RobotFileParser(robots_url)
    parser.read()
    for path in (*collection_paths, "/sample-product.json"):
        if not parser.can_fetch(USER_AGENT, f"{BASE_URL}{path}"):
            raise RuntimeError(f"robots.txt không cho phép truy cập {path}")


def product_paths(
    collection_paths: list[str], page_count: int, delay: float, available_only: bool
) -> list[tuple[str, str]]:
    paths: list[tuple[str, str]] = []
    seen: set[str] = set()
    pattern = re.compile(
        r'<a\s+class="image_thumb[^"]*"\s+href="([^"]+)"',
        re.IGNORECASE,
    )
    marker = '<div class="item_product_main">'
    for collection_path in collection_paths:
        for page in range(1, page_count + 1):
            url = f"{BASE_URL}{collection_path}?page={page}"
            try:
                text = fetch(url, timeout=60).decode("utf-8", errors="replace")
            except Exception as exc:
                print(f"[cảnh báo] Không tải được {url}: {exc}")
                continue
            cards = text.split(marker)[1:]
            if not cards:
                break
            new_on_page = 0
            for card in cards:
                if available_only and 'class="soldout"' in card:
                    continue
                match = pattern.search(card)
                if not match:
                    continue
                path = urllib.parse.urlparse(match.group(1)).path.rstrip("/")
                if path and path not in seen:
                    seen.add(path)
                    paths.append((path, collection_path))
                    new_on_page += 1
            print(
                f"[collection] {collection_path} page={page}: "
                f"{new_on_page} ứng viên mới"
            )
            time.sleep(delay)
    return paths


def collection_products(
    collection_paths: list[str], available_only: bool, delay: float
) -> list[tuple[dict, str]]:
    products: list[tuple[dict, str]] = []
    seen: set[str] = set()
    for collection_path in collection_paths:
        alias = collection_path.strip("/")
        url = f"{BASE_URL}/collections/{alias}/products.json?limit=250"
        try:
            payload = json.loads(fetch(url, timeout=60).decode("utf-8"))
        except Exception as exc:
            print(f"[cảnh báo] Không tải được {url}: {exc}")
            continue
        new_count = 0
        for product in payload.get("products") or []:
            source_id = str(product.get("id"))
            if not source_id or source_id in seen:
                continue
            if available_only and not bool(product.get("available")):
                continue
            seen.add(source_id)
            products.append((product, collection_path))
            new_count += 1
        print(
            f"[collection-json] {collection_path}: {new_count} ứng viên mới "
            f"trên {len(payload.get('products') or [])} sản phẩm"
        )
        time.sleep(delay)
    return products


def tag_attributes(tags: list[str] | str | None) -> dict[str, str]:
    if isinstance(tags, str):
        values = [part.strip() for part in tags.split(",")]
    else:
        values = tags or []
    prefixes = {
        "thuonghieu_": "brand_tag",
        "mausac_": "color_vi",
        "sanxuat_": "country",
        "xuatxu_": "origin",
        "chatlieu_": "material",
        "kichthuoc_": "dimensions",
    }
    result: dict[str, str] = {}
    for value in values:
        for prefix, key in prefixes.items():
            if value.lower().startswith(prefix):
                result[key] = value[len(prefix) :].strip()
    return result


def category_for(name: str, product_type: str) -> str:
    value = f"{name} {product_type}".lower()
    if re.search(r"\b(bút|mực|marker|highlight)", value):
        return "but-viet"
    if re.search(r"\b(sổ|vở|giấy|note)", value):
        return "so-giay"
    if re.search(r"\b(bìa|file|folder|kẹp tài liệu|hồ sơ)", value):
        return "luu-tru"
    if re.search(r"\b(kéo|thước|ghim|dập|bấm|đục lỗ|dao|gọt|keo dán)", value):
        return "dung-cu"
    return "do-ban"


def color_en(value: str) -> str:
    normalized = (value or "").lower()
    mapping = {
        "đen": "black",
        "trắng": "white",
        "xám": "grey",
        "ghi": "grey",
        "đỏ": "red",
        "xanh lá": "green",
        "xanh dương": "blue",
        "xanh": "blue",
        "nâu": "brown",
        "vàng": "yellow",
        "cam": "orange",
        "hồng": "pink",
        "tím": "purple",
    }
    for vietnamese, english in mapping.items():
        if vietnamese in normalized:
            return english
    return "multicolor"


def extension_for(url: str) -> str:
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"


def scrape(args: argparse.Namespace) -> None:
    collection_paths = [
        value if value.startswith("/") else f"/{value}"
        for value in args.collections
    ]
    check_robots(collection_paths)
    root = Path(args.output).resolve()
    image_dir = root / "images"
    root.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    if args.collection_json:
        candidates: list[tuple[dict | str, str]] = collection_products(
            collection_paths, args.available_only, args.delay
        )
    else:
        candidates = product_paths(
            collection_paths, args.pages, args.delay, args.available_only
        )
    excluded_ids: set[str] = set()
    for excluded_value in args.exclude_datasets or []:
        excluded_path = Path(excluded_value)
        if excluded_path.exists():
            excluded_ids.update(
                str(json.loads(line).get("source_id"))
                for line in excluded_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
    if excluded_ids:
        print(f"[lọc trùng] {len(excluded_ids)} mã từ dataset đã có")
    collected_at = datetime.now(timezone.utc).isoformat()
    records: list[dict] = []

    for candidate_index, (candidate, collection_path) in enumerate(candidates, start=1):
        if isinstance(candidate, dict):
            payload = candidate
            product_path = payload.get("url") or f"/{payload.get('alias', '')}"
            source_url = urllib.parse.urljoin(BASE_URL, str(product_path))
        else:
            source_url = f"{BASE_URL}{candidate}"
            try:
                payload = json.loads(fetch(f"{source_url}.json", timeout=60).decode("utf-8"))
            except Exception as exc:
                print(f"[cảnh báo] Bỏ qua {source_url}: {exc}")
                continue
        if str(payload.get("id")) in excluded_ids:
            continue
        if args.available_only and not bool(payload.get("available")):
            continue
        attributes = tag_attributes(payload.get("tags"))
        images = [str(value) for value in payload.get("images") or []]
        local_images: list[str] = []

        for image_index, image_url in enumerate(images[: args.images_per_product], start=1):
            extension = extension_for(image_url)
            filename = f"ADC{payload['id']}_{image_index:02d}{extension}"
            destination = image_dir / filename
            if not destination.exists():
                destination.write_bytes(fetch(image_url))
                time.sleep(args.image_delay)
            local_images.append(f"images/{filename}")

        color_vi = attributes.get("color_vi", "Nhiều màu")
        record = {
            "source_id": payload.get("id"),
            "source": "ADCBook Store",
            "source_url": source_url,
            "source_collection": f"{BASE_URL}{collection_path}",
            "scraped_at_utc": collected_at,
            "name_vi": payload.get("name", ""),
            "brand": attributes.get("brand_tag") or payload.get("vendor", ""),
            "vendor": payload.get("vendor", ""),
            "product_type": payload.get("product_type", ""),
            "category": category_for(payload.get("name", ""), payload.get("product_type", "")),
            "color_vi": color_vi,
            "color": color_en(color_vi),
            "material": attributes.get("material", ""),
            "dimensions": attributes.get("dimensions", ""),
            "origin": attributes.get("origin") or attributes.get("country", ""),
            "price_vnd": payload.get("price") or 0,
            "compare_at_price_vnd": payload.get("compare_at_price") or 0,
            "available": bool(payload.get("available")),
            "description_vi": html_to_text(payload.get("content") or payload.get("summary")),
            "image_urls": images,
            "local_images": local_images,
            "image_rights_note": RIGHTS_NOTE,
        }
        records.append(record)
        print(
            f"[{len(records):02d}/{args.limit:02d}] {record['name_vi']} "
            f"(ứng viên {candidate_index}/{len(candidates)})"
        )
        if len(records) >= args.limit:
            break
        time.sleep(args.delay)

    jsonl_path = root / "products.jsonl"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")

    csv_path = root / "products.csv"
    fields = [
        "source_id",
        "name_vi",
        "brand",
        "product_type",
        "category",
        "color_vi",
        "color",
        "price_vnd",
        "compare_at_price_vnd",
        "available",
        "material",
        "dimensions",
        "origin",
        "description_vi",
        "source_url",
        "first_image_url",
        "first_local_image",
        "image_rights_note",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["first_image_url"] = (record["image_urls"] or [""])[0]
            row["first_local_image"] = (record["local_images"] or [""])[0]
            writer.writerow({key: row.get(key, "") for key in fields})

    readme = root / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# ADCBook Vietnamese Stationery Sample",
                "",
                f"- Số sản phẩm: {len(records)}",
                f"- Collection nguồn: {', '.join(BASE_URL + value for value in collection_paths)}",
                f"- Thời điểm thu thập UTC: {collected_at}",
                "- Cách thu thập: collection công khai và endpoint JSON sản phẩm; không truy cập search/cart/account/checkout.",
                f"- Quyền ảnh: {RIGHTS_NOTE}",
                "",
                "`products.jsonl` giữ đầy đủ danh sách ảnh; `products.csv` thuận tiện để kiểm tra và nhập SQL Server.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"\nHoàn tất: {len(records)} sản phẩm, {sum(len(x['local_images']) for x in records)} ảnh")
    print(jsonl_path)
    print(csv_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="datasets/adcbook_stationery")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--collections", nargs="+", default=DEFAULT_COLLECTIONS)
    parser.add_argument("--available-only", action="store_true")
    parser.add_argument("--collection-json", action="store_true")
    parser.add_argument("--exclude-datasets", nargs="+")
    parser.add_argument("--images-per-product", type=int, default=1)
    parser.add_argument("--delay", type=float, default=0.75)
    parser.add_argument("--image-delay", type=float, default=0.2)
    scrape(parser.parse_args())


if __name__ == "__main__":
    main()

