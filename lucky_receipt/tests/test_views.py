from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from lucky_receipt.models import Receipt

User = get_user_model()


def _dt():
    d = settings.PROMO_START_DATE
    return timezone.make_aware(
        timezone.datetime(d.year, d.month, d.day, 12, 0),
        settings.PROMO_TIMEZONE,
    )


class ReceiptViewTests(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user("u1", password="p")
        self.u2 = User.objects.create_user("u2", password="p")
        self.client.force_login(self.u1)

    def test_create_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("receipts:create"))
        assert isinstance(resp, HttpResponseRedirect)
        assert "/accounts/login/" in resp.url

    def test_create_sets_pending_and_user(self):
        resp = self.client.post(reverse("receipts:create"), {
            "fn": "1", "fd": "2", "fp": "3",
            "purchased_at": _dt().strftime("%Y-%m-%dT%H:%M"),
            "amount": "1500",
        })
        assert isinstance(resp, HttpResponseRedirect)
        r = Receipt.objects.get()
        assert r.user == self.u1
        assert r.status == Receipt.Status.PENDING

    def test_list_only_own_receipts(self):
        Receipt.objects.create(user=self.u1, fn="1", fd="1", fp="1",
                               purchased_at=_dt(), amount=Decimal("1000"))
        Receipt.objects.create(user=self.u2, fn="2", fd="2", fp="2",
                               purchased_at=_dt(), amount=Decimal("1000"))
        resp = self.client.get(reverse("receipts:list"))
        assert isinstance(resp, TemplateResponse)
        ctx = resp.context_data
        assert ctx is not None
        page_receipts = list(ctx["receipts"])
        assert len(page_receipts) == 1
        assert page_receipts[0].user_id == self.u1.id

    def test_pagination(self):
        for i in range(15):
            Receipt.objects.create(
                user=self.u1,
                fn=str(1000 + i), fd=str(i), fp=str(i),
                purchased_at=_dt(), amount=Decimal("1000"),
            )
        resp = self.client.get(reverse("receipts:list"))
        assert isinstance(resp, TemplateResponse)
        ctx = resp.context_data
        assert ctx is not None
        assert len(list(ctx["receipts"])) == 10
        assert ctx["is_paginated"]

    def test_api_only_own(self):
        Receipt.objects.create(user=self.u1, fn="1", fd="1", fp="1",
                               purchased_at=_dt(), amount=Decimal("1000"))
        Receipt.objects.create(user=self.u2, fn="2", fd="2", fp="2",
                               purchased_at=_dt(), amount=Decimal("1000"))
        resp = self.client.get(reverse("receipts:api_list"))
        assert isinstance(resp, JsonResponse)
        data = resp.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["fn"] == "1"

    def test_api_ignores_query_params(self):
        Receipt.objects.create(user=self.u2, fn="2", fd="2", fp="2",
                               purchased_at=_dt(), amount=Decimal("1000"))
        resp = self.client.get(
            reverse("receipts:api_list") + f"?user_id={self.u2.id}"
        )
        assert isinstance(resp, JsonResponse)
        assert resp.json()["results"] == []

    def test_api_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("receipts:api_list"))
        assert isinstance(resp, HttpResponseRedirect)
        assert resp.status_code == 302
