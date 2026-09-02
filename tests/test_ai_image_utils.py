import io

import pytest
from PIL import Image

from app.ai.image_utils import STRIPPED_MEDIA_TYPE, InvalidImageError, strip_image_metadata


def _make_png_with_exif() -> bytes:
    image = Image.new("RGB", (20, 10), color=(255, 0, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_strip_image_metadata_returns_jpeg() -> None:
    data, media_type = strip_image_metadata(_make_png_with_exif())

    assert media_type == STRIPPED_MEDIA_TYPE
    with Image.open(io.BytesIO(data)) as reopened:
        assert reopened.format == "JPEG"
        assert reopened.mode == "RGB"
        assert reopened.size == (20, 10)


def test_strip_image_metadata_drops_exif() -> None:
    image = Image.new("RGB", (5, 5))
    exif = image.getexif()
    exif[0x0110] = "Some Camera Model"  # Model tag
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)

    data, _ = strip_image_metadata(buffer.getvalue())

    with Image.open(io.BytesIO(data)) as reopened:
        assert not reopened.getexif()


def test_strip_image_metadata_rejects_garbage() -> None:
    with pytest.raises(InvalidImageError):
        strip_image_metadata(b"this is not an image")
