import io
import os

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


_EXT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}
_CT = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "GIF": "image/gif",
}


def make_test_image(
    fmt: str = "JPEG",
    size: tuple[int, int] = (400, 400),
) -> SimpleUploadedFile:
    """Возвращает SimpleUploadedFile с шумной картинкой.

    Шум (случайные пиксели) не сжимается в разы, поэтому файл получается
    размером в десятки килобайт — похоже на реальное фото чека.
    """
    w, h = size
    raw = os.urandom(w * h * 3)
    img = Image.frombytes("RGB", (w, h), raw)

    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)

    ext = _EXT.get(fmt, fmt.lower())
    ct = _CT.get(fmt, "application/octet-stream")
    return SimpleUploadedFile(f"test.{ext}", buf.read(), content_type=ct)
