"""Validated catalogue references and private, expiring query media."""
from pathlib import Path
from urllib.parse import urlsplit
from backend.shared.paths import PROJECT_ROOT
from backend.shared.validation import require

PUBLIC=PROJECT_ROOT/'frontend/public'
ASSETS=PUBLIC/'assets'


def validate_image_reference(reference):
    if not reference.startswith('/assets/'):
        try:
            url = urlsplit(reference)
            valid = url.scheme in ('http', 'https') and bool(url.hostname) and not url.username and not url.password and not any(c.isspace() for c in reference)
        except ValueError:
            valid = False
        require(valid, 'Nhập link ảnh http/https hợp lệ hoặc chọn ảnh trong /assets/.')
        return reference
    target=(ASSETS/reference.removeprefix('/assets/')).resolve()
    require(reference.startswith('/assets/') and target.is_relative_to(ASSETS.resolve()) and target.is_file(),'Chọn ảnh catalogue trong /assets/.')
    return reference


def image_path(reference):
    if not reference.startswith('/assets/'):
        return None
    path=(PUBLIC/reference.lstrip('/')).resolve()
    if path.is_relative_to(PUBLIC.resolve()) and path.is_file():
        return path
    return None


def store_query_image(raw, directory):
    from datetime import datetime, timezone, timedelta
    from uuid import uuid4
    from io import BytesIO
    from PIL import Image
    import time
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for previous in directory.glob('*.png'):
        if previous.stat().st_mtime < time.time()-86400:
            previous.unlink(missing_ok=True)
    path=directory/(str(uuid4())+'.png')
    with Image.open(BytesIO(raw)) as source:
        source.convert('RGB').save(path,format='PNG')
    return {'reference':str(path),'mime_type':'image/png','size':path.stat().st_size,'expires_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(timespec='seconds')}
