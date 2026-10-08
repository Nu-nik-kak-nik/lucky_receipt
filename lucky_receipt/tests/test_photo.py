import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from lucky_receipt.models import Receipt, ReceiptPhoto
from lucky_receipt.validators import validate_receipt_photo
from django.core.exceptions import ValidationError

from .factories import make_test_image

User = get_user_model()


class PhotoValidatorTests(TestCase):
    def test_valid_jpeg(self):
        validate_receipt_photo(make_test_image("JPEG"))

    def test_valid_png(self):
        validate_receipt_photo(make_test_image("PNG"))

    def test_valid_webp(self):
        validate_receipt_photo(make_test_image("WEBP"))

    def test_unsupported_format_gif(self):
        buf = make_test_image("GIF")
        with self.assertRaises(ValidationError):
            validate_receipt_photo(buf)

    def test_too_large(self):
        big = SimpleUploadedFile(
            "big.jpg",
            b"\xff" * (6 * 1024 * 1024),
            content_type="image/jpeg",
        )
        with self.assertRaises(ValidationError):
            validate_receipt_photo(big)

    def test_too_small(self):
        tiny = SimpleUploadedFile(
            "tiny.jpg",
            b"\xff" * 100,
            content_type="image/jpeg",
        )
        with self.assertRaises(ValidationError):
            validate_receipt_photo(tiny)

    def test_not_image(self):
        bogus = SimpleUploadedFile(
            "bogus.jpg",
            b"this is not an image at all" * 1000,
            content_type="image/jpeg",
        )
        with self.assertRaises(ValidationError):
            validate_receipt_photo(bogus)


class PhotoModelTests(TestCase):
    def test_creates_photo_for_receipt(self):
        user = User.objects.create_user("u", password="p")
        r = Receipt.objects.create(
            user=user, fn="1", fd="1", fp="1",
            purchased_at="2026-10-01T12:00:00+03:00",
            amount="1500",
        )
        f = SimpleUploadedFile("p.jpg", make_test_image().read(), content_type="image/jpeg")
        p = ReceiptPhoto.objects.create(receipt=r, image=f)
        assert p.pk is not None
        assert r.photos.count() == 1
