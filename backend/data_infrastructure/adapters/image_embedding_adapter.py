"""Existing colour/layout baseline; no semantic embedding model is configured."""
import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from backend.shared.validation import require


def descriptor(image):
    image=ImageOps.fit(image.convert('RGB'),(16,16))
    return [v/255 for pixel in image.get_flattened_data() for v in pixel]


def encode_query(raw):
    require(len(raw)<=5*1024*1024,'Ảnh tối đa 5 MB.',413)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                require(image.format in ['JPEG','PNG','WEBP'],'Định dạng ảnh không hỗ trợ.')
                require(image.width*image.height<=16000000,'Ảnh tối đa 16 triệu pixel.')
                image.load()
                return descriptor(image)
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        require(False,'Không đọc được ảnh. Thử ảnh khác hoặc tìm bằng từ khoá.')


def encode_catalogue(path):
    with Image.open(path) as image:
        return descriptor(image)
