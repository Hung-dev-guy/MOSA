import pytest

from backend.data_infrastructure.storage.image_storage import image_path, validate_image_reference
from backend.shared.validation import Problem


@pytest.mark.parametrize('reference', ['/assets/pen-blue.png', 'https://example.com/photo.jpg?size=large', 'http://example.com/photo.png'])
def test_accepts_catalogue_images_and_web_links(reference):
    assert validate_image_reference(reference) == reference


@pytest.mark.parametrize('reference', ['javascript:alert(1)', 'data:image/png;base64,abc', '//example.com/a.png', 'https:///a.png', 'https://[bad/a.png', 'https://example.com/a b.png', 'https://user:password@example.com/a.png', '/assets/../package.json', '/assets/missing.png'])
def test_rejects_invalid_images(reference):
    with pytest.raises(Problem):
        validate_image_reference(reference)


def test_remote_images_are_not_local_search_files():
    assert image_path('https://example.com/photo.jpg') is None
    assert image_path('/assets/pen-blue.png').is_file()
