from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from lucky_receipt.forms import ReceiptForm
from lucky_receipt.models import Receipt

User = get_user_model()


def _within_period():
    d = settings.PROMO_START_DATE + (settings.PROMO_END_DATE - settings.PROMO_START_DATE) / 2
    return timezone.make_aware(
        timezone.datetime(d.year, d.month, d.day, 12, 0),
        settings.PROMO_TIMEZONE,
    )


class ReceiptFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="p")

    def _data(self, **overrides):
        base = {
            "fn": "1234567890123456",
            "fd": "12345",
            "fp": "9876543210",
            "purchased_at": _within_period().strftime("%Y-%m-%dT%H:%M"),
            "amount": "1500.00",
        }
        base.update(overrides)
        return base

    def test_valid(self):
        form = ReceiptForm(data=self._data())
        assert form.is_valid(), form.errors

    def test_amount_below_min(self):
        form = ReceiptForm(data=self._data(amount="999.99"))
        assert not form.is_valid()
        assert form.has_error("amount")

    def test_date_before_period(self):
        before = settings.PROMO_START_DATE - timedelta(days=1)
        dt = timezone.make_aware(
            timezone.datetime(before.year, before.month, before.day, 12, 0),
            settings.PROMO_TIMEZONE,
        )
        form = ReceiptForm(data=self._data(purchased_at=dt.strftime("%Y-%m-%dT%H:%M")))
        assert not form.is_valid()
        assert form.has_error("purchased_at")

    def test_date_after_period(self):
        after = settings.PROMO_END_DATE + timedelta(days=1)
        dt = timezone.make_aware(
            timezone.datetime(after.year, after.month, after.day, 12, 0),
            settings.PROMO_TIMEZONE,
        )
        form = ReceiptForm(data=self._data(purchased_at=dt.strftime("%Y-%m-%dT%H:%M")))
        assert not form.is_valid()
        assert form.has_error("purchased_at")

    def test_fd_non_digit(self):
        form = ReceiptForm(data=self._data(fd="abc"))
        assert not form.is_valid()
        assert form.has_error("fd")

    def test_duplicate_fiscal_triple(self):
        Receipt.objects.create(
            user=self.user, fn="1234567890123456", fd="12345", fp="9876543210",
            purchased_at=_within_period(), amount=Decimal("1000"),
        )
        form = ReceiptForm(data=self._data())
        assert not form.is_valid()
        assert form.has_error("__all__")

    def test_qr_autofills_fields(self):
        qr = f"t={_within_period():%Y%m%dT%H%M}&s=1500.00&fn=111&i=222&fp=333"
        form = ReceiptForm(data={"qr_string": qr})
        assert form.is_valid(), form.errors
        assert form.cleaned_data["fn"] == "111"
        assert form.cleaned_data["fd"] == "222"
        assert form.cleaned_data["fp"] == "333"
        assert form.cleaned_data["amount"] == Decimal("1500.00")

    def test_qr_does_not_override_manual(self):
        qr = f"t={_within_period():%Y%m%dT%H%M}&s=1500.00&fn=111&i=222&fp=333"
        form = ReceiptForm(data={
            "qr_string": qr,
            "fn": "999", "fd": "888", "fp": "777",
            "amount": "2000",
            "purchased_at": _within_period().strftime("%Y-%m-%dT%H:%M"),
        })
        assert form.is_valid(), form.errors
        assert form.cleaned_data["fn"] == "999"

    def test_invalid_qr_shows_error(self):
        form = ReceiptForm(data={"qr_string": "totally-broken"})
        assert not form.is_valid()
        assert form.has_error("qr_string")
