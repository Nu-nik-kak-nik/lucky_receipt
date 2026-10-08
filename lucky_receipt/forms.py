from datetime import datetime, time
from decimal import Decimal

from django import forms
from django.conf import settings
from django.utils import timezone

from .models import Receipt


class ReceiptForm(forms.ModelForm):
    class Meta:
        model = Receipt
        fields = ("fn", "fd", "fp", "purchased_at", "amount")
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
        super().__init__(*args, **kwargs)

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
                "data-validate": "digits",
            })

        self.fields["amount"].widget.attrs.update({
            "min": "0",
            "step": "0.01",
            "inputmode": "decimal",
            "data-validate": "amount",
            "data-min-amount": str(settings.PROMO_MIN_AMOUNT),
        })

        self.fields["purchased_at"].widget.attrs.update({
            "data-validate": "date",
            "data-date-min": settings.PROMO_START_DATE.isoformat(),
            "data-date-max": settings.PROMO_END_DATE.isoformat(),
        })

    def _clean_digits(self, field_name: str) -> str:
        value = (self.cleaned_data.get(field_name) or "").strip()
        if not value:
            raise forms.ValidationError("Обязательное поле")
        if not value.isdigit():
            raise forms.ValidationError("Допустимы только цифры")
        return value

    def clean_fn(self):
        return self._clean_digits("fn")

    def clean_fd(self):
        return self._clean_digits("fd")

    def clean_fp(self):
        return self._clean_digits("fp")

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount < settings.PROMO_MIN_AMOUNT:
            raise forms.ValidationError(
                f"Сумма чека должна быть не меньше {settings.PROMO_MIN_AMOUNT} ₽"
            )
        return amount

    def clean_purchased_at(self):
        value = self.cleaned_data["purchased_at"]

        if timezone.is_naive(value):
            value = timezone.make_aware(value, settings.PROMO_TIMEZONE)

        start = datetime.combine(
            settings.PROMO_START_DATE,
            time.min,
            tzinfo=settings.PROMO_TIMEZONE,
        )
        end = datetime.combine(
            settings.PROMO_END_DATE,
            time.max,
            tzinfo=settings.PROMO_TIMEZONE,
        )

        if not (start <= value <= end):
            raise forms.ValidationError(
                "Дата покупки должна быть в период акции "
                f"с {settings.PROMO_START_DATE:%d.%m.%Y} "
                f"по {settings.PROMO_END_DATE:%d.%m.%Y}"
            )

        return value

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
                raise forms.ValidationError(
                    "Чек с такими ФН, ФД и ФП уже зарегистрирован"
                )

        return cleaned
