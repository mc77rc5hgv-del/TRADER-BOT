"""Screenshot validation and metadata stripping (TZ section 91: "stripping
metadata" is one of the required safeguards before a user-uploaded image is
stored or sent anywhere)."""

from __future__ import annotations

import io

from PIL import Image, UnidentifiedImageError

STRIPPED_MEDIA_TYPE = "image/jpeg"


class InvalidImageError(Exception):
    """The uploaded file isn't a decodable image."""


def strip_image_metadata(data: bytes) -> tuple[bytes, str]:
    """Re-encodes the image as a fresh JPEG, dropping EXIF/ICC/XMP metadata
    (Pillow's save() doesn't carry those over unless explicitly asked to).
    Runs synchronously/CPU-bound — call via asyncio.to_thread from async code."""
    try:
        with Image.open(io.BytesIO(data)) as image:
            rgb_image = image.convert("RGB")
    except UnidentifiedImageError as exc:
        raise InvalidImageError("Not a decodable image") from exc

    buffer = io.BytesIO()
    rgb_image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue(), STRIPPED_MEDIA_TYPE
