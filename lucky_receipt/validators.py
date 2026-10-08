from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_PHOTO_BYTES = 5 * 1024 * 1024
MIN_PHOTO_BYTES = 1 * 1024

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def validate_receipt_photo(file) -> None:
    """Проверяет формат (Pillow), расширение и размер файла фото чека."""
    if file is None:
        return

    size = getattr(file, "size", None)
    if size is None:
        try:
            pos = file.tell()
            file.seek(0, 2)
            size = file.tell()
            file.seek(pos)
        except (AttributeError, OSError):
            raise ValidationError("Не удалось прочитать размер файла")

    if size > MAX_PHOTO_BYTES:
        raise ValidationError(
            f"Размер файла не должен превышать "
            f"{MAX_PHOTO_BYTES // (1024 * 1024)} МБ"
        )
    if size < MIN_PHOTO_BYTES:
        raise ValidationError("Файл слишком маленький — возможно, он повреждён")

    name = getattr(file, "name", "") or ""
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError("Расширение файла должно быть .jpg, .jpeg, .png или .webp")

    pos = file.tell() if hasattr(file, "tell") else 0
    try:
        img = Image.open(file)
        fmt = (img.format or "").upper()
    except (UnidentifiedImageError, OSError):
        raise ValidationError("Не удалось распознать изображение")
    finally:
        try:
            file.seek(pos)
        except (AttributeError, OSError):
            pass

    if fmt not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError("Поддерживаются только форматы JPEG, PNG и WEBP")
