from flask import Blueprint, jsonify, request

from backend.application import search_orchestrator
from backend.shared.validation import require

bp=Blueprint('search_controller',__name__)


@bp.get('/api/products')
def products():
    return jsonify(search_orchestrator.catalogue(request.args))


@bp.post('/api/search/image')
def image_search():
    upload=request.files.get('image')
    require(upload is not None,'Chọn ảnh JPEG, PNG hoặc WebP.')
    return jsonify(search_orchestrator.image_search(upload.read(5*1024*1024+1),request.args))
