from datetime import datetime, time
from decimal import Decimal

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Receipt
from .services import QRParseError, parse_qr_string


class ReceiptForm(forms.ModelForm):
    qr_string = forms.CharField(
        required=False,
        label="Вставить строку из QR-кода",
        widget=forms.TextInput(attrs={
            "placeholder": "t=20250101T1200&s=1500.00&fn=...&i=...&fp=...",
            "autocomplete": "off",
        }),
        help_text="Необязательно. Если заполнено — поля ниже подставятся автоматически.",
    )

    class Meta:
        model = Receipt
        fields = ("qr_string", "fn", "fd", "fp", "purchased_at", "amount")
        labels = {
            "fn": "ФН",
            "fd": "ФД",
            "fp": "ФП",
            "purchased_at": "Дата и время покупки",
            "amount": "Сумма, ₽",
        }
        widgets = {
            "purchased_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        data = kwargs.get("data") if "data" in kwargs else (args[0] if args else None)
        if data is not None:
            data = self._fill_from_qr(data)
            if "data" in kwargs:
                kwargs["data"] = data
            else:
                args = (data, *args[1:])
        super().__init__(*args, **kwargs)
        self._configure_widgets()

    @staticmethod
    def _fill_from_qr(data):
        try:
            raw = (data.get("qr_string") or "").strip()
        except AttributeError:
            return data
        if not raw:
            return data

        try:
            parsed = parse_qr_string(raw)
        except QRParseError:
            return data

        data = data.copy()
        if not (data.get("fn") or "").strip():
            data["fn"] = parsed.fn
        if not (data.get("fd") or "").strip():
            data["fd"] = parsed.fd
        if not (data.get("fp") or "").strip():
            data["fp"] = parsed.fp
        if not (data.get("amount") or "").strip():
            data["amount"] = str(parsed.amount)
        if not (data.get("purchased_at") or "").strip():
            data["purchased_at"] = parsed.purchased_at.strftime("%Y-%m-%dT%H:%M")
        return data

    def _configure_widgets(self):
        self.fields["purchased_at"].input_formats = [
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
        ]

        for name in ("fn", "fd", "fp"):
            self.fields[name].widget.attrs.update({
                "inputmode": "numeric",
                "autocomplete": "off",
                "pattern": r"\d+",
            })

        self.fields["amount"].widget.attrs.update({
            "min": "0",
            "step": "1",
            "inputmode": "decimal",
            "data-min-amount": str(settings.PROMO_MIN_AMOUNT),
        })

        self.fields["purchased_at"].widget.attrs.update({
            "data-date-min": settings.PROMO_START_DATE.isoformat(),
            "data-date-max": settings.PROMO_END_DATE.isoformat(),
        })

    @staticmethod
    def _validate_digits(value: str | None, label: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValidationError("Обязательное поле")
        if not value.isdigit():
            raise ValidationError("Допустимы только цифры")
        return value

    @staticmethod
    def _validate_amount(value: Decimal) -> "Decimal":
        if value < settings.PROMO_MIN_AMOUNT:
            raise ValidationError(
                f"Сумма чека должна быть не меньше {settings.PROMO_MIN_AMOUNT} ₽"
            )
        return value

    @staticmethod
    def _validate_purchased_at(value: datetime) -> datetime:
        if timezone.is_naive(value):
            value = timezone.make_aware(value, settings.PROMO_TIMEZONE)

        start = datetime.combine(settings.PROMO_START_DATE, time.min, tzinfo=settings.PROMO_TIMEZONE)
        end = datetime.combine(settings.PROMO_END_DATE, time.max, tzinfo=settings.PROMO_TIMEZONE)

        if not (start <= value <= end):
            raise ValidationError(
                "Дата покупки должна быть в период акции "
                f"с {settings.PROMO_START_DATE:%d.%m.%Y} по {settings.PROMO_END_DATE:%d.%m.%Y}"
            )
        return value


    def clean_fn(self):
        return self._validate_digits(self.cleaned_data.get("fn"), "ФН")

    def clean_fd(self):
        return self._validate_digits(self.cleaned_data.get("fd"), "ФД")

    def clean_fp(self):
        return self._validate_digits(self.cleaned_data.get("fp"), "ФП")

    def clean_amount(self):
        return self._validate_amount(self.cleaned_data["amount"])

    def clean_purchased_at(self):
        return self._validate_purchased_at(self.cleaned_data["purchased_at"])

    def clean_qr_string(self):
        raw = (self.cleaned_data.get("qr_string") or "").strip()
        if not raw:
            return ""
        try:
            parse_qr_string(raw)
        except QRParseError as exc:
            raise ValidationError(str(exc))
        return raw

    def clean(self):
        cleaned = super().clean()
        fn = cleaned.get("fn")
        fd = cleaned.get("fd")
        fp = cleaned.get("fp")

        if fn and fd and fp:
            qs = Receipt.objects.filter(fn=fn, fd=fd, fp=fp)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Чек с такими ФН, ФД и ФП уже зарегистрирован")

        return cleaned
