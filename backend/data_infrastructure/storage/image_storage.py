"""Catalogue image paths. User search images are never persisted."""
from backend.shared.paths import PROJECT_ROOT
from backend.shared.validation import require

PUBLIC=PROJECT_ROOT/'frontend/public'
ASSETS=PUBLIC/'assets'


def validate_image_reference(reference):
    target=(ASSETS/reference.removeprefix('/assets/')).resolve()
    require(reference.startswith('/assets/') and target.is_relative_to(ASSETS.resolve()) and target.is_file(),'Chọn ảnh catalogue trong /assets/.')
    return reference


def image_path(reference):
    path=(PUBLIC/reference.lstrip('/')).resolve()
    if path.is_relative_to(PUBLIC.resolve()) and path.is_file():
        return path
    return None
