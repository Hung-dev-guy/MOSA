from flask import Blueprint, send_from_directory

from backend.shared.paths import PROJECT_ROOT
from backend.shared.validation import require

bp=Blueprint('web',__name__)


@bp.get('/assets/<path:path>')
def assets(path):
    compiled=PROJECT_ROOT/'frontend/dist/assets'
    if (compiled/path).is_file():
        return send_from_directory(compiled,path)
    return send_from_directory(PROJECT_ROOT/'frontend/public/assets',path)


@bp.get('/')
@bp.get('/<path:path>')
def frontend(path=''):
    require(not path.startswith('api/'),'Không có API này.',404)
    dist=PROJECT_ROOT/'frontend/dist'
    if path and (dist/path).is_file():
        return send_from_directory(dist,path)
    return send_from_directory(dist,'index.html')
