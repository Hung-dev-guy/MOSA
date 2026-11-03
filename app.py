import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from PIL import UnidentifiedImageError
from werkzeug.exceptions import HTTPException

from src.application.search import DominantColorImageEncoder, RankingService, SearchOrchestrator
from src.domain.models import SearchRequest
from src.infrastructure.database import SqlServerConnectionFactory
from src.infrastructure.product_repository import ProductRepository


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

connection_factory = SqlServerConnectionFactory()
repository = ProductRepository(connection_factory)
orchestrator = SearchOrchestrator(repository, RankingService(), DominantColorImageEncoder())


@app.after_request
def disable_api_cache(response):
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@app.get("/")
def home():
    return render_template("index.html", currency=os.getenv("APP_CURRENCY", "VND"))


@app.get("/favicon.ico")
def favicon():
    return "", 204


@app.get("/api/health")
def health():
    with connection_factory.connect() as connection:
        connection.cursor().execute("SELECT 1").fetchval()
    return jsonify({"status": "ok", "database": "connected"})


@app.get("/api/home")
def home_data():
    result = orchestrator.search(SearchRequest(mode="text", limit=100))
    return jsonify(
        {
            "categories": repository.categories(),
            "products": result["results"],
            "currency": os.getenv("APP_CURRENCY", "VND"),
        }
    )


@app.post("/api/search/<mode>")
def search(mode: str):
    if mode == "image":
        upload = request.files.get("image")
        if not upload or not upload.filename:
            return jsonify({"error": "Vui lòng chọn một ảnh sản phẩm."}), 400
        if upload.mimetype not in {"image/jpeg", "image/png", "image/webp"}:
            return jsonify({"error": "Chỉ hỗ trợ JPG, PNG hoặc WebP."}), 400
        try:
            return jsonify(
                orchestrator.search_image(
                    upload.read(),
                    request.form.get("query", "").strip(),
                    request.form.get("category", "").strip(),
                )
            )
        except UnidentifiedImageError:
            return jsonify({"error": "Tệp tải lên không phải ảnh hợp lệ."}), 400

    payload = request.get_json(silent=True) or {}
    query = str(payload.get("query", "")).strip()
    if not query:
        return jsonify({"error": "Vui lòng nhập nội dung tìm kiếm."}), 400
    return jsonify(
        orchestrator.search(
            SearchRequest(
                mode=mode,
                query=query,
                category=str(payload.get("category", "")).strip(),
            )
        )
    )


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify({"error": "Ảnh vượt quá giới hạn 8 MB."}), 413


@app.errorhandler(HTTPException)
def http_error(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": error.description}), error.code
    return error


@app.errorhandler(Exception)
def unexpected_error(error):
    app.logger.exception(error)
    return jsonify({"error": "Không thể xử lý yêu cầu. Hãy kiểm tra kết nối SQL Server."}), 500


if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5050")),
        debug=False,
    )

