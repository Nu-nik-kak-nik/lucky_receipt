from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from lucky_receipt.models import Receipt

User = get_user_model()


class AdminTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            "mod", password="p", is_staff=True, is_superuser=True
        )
        self.user = User.objects.create_user("u", password="p")
        self.client.force_login(self.staff)

    def _mk(self, **overrides):
        d = settings.PROMO_START_DATE
        dt = timezone.make_aware(
            timezone.datetime(d.year, d.month, d.day, 12, 0),
            settings.PROMO_TIMEZONE,
        )
        base = dict(
            user=self.user,
            fn="1", fd="1", fp="1",
            purchased_at=dt,
            amount=Decimal("1500"),
            status=Receipt.Status.PENDING,
        )
        base.update(overrides)
        return Receipt.objects.create(**base)

    def test_accepted_can_have_comment(self):
        r = self._mk()
        resp = self.client.post(
            reverse("admin:lucky_receipt_receipt_change", args=[r.id]),
            {
                "user": self.user.id,
                "fn": r.fn, "fd": r.fd, "fp": r.fp,
                "purchased_at_0": r.purchased_at.strftime("%Y-%m-%d"),
                "purchased_at_1": r.purchased_at.strftime("%H:%M:%S"),
                "amount": "1500",
                "status": Receipt.Status.ACCEPTED,
                "moderator_comment": "Ваш приз ждёт вас — сходите на почту.",
            },
        )
        # При принятии с комментарием — всё ок, редирект на список
        assert resp.status_code == 302
        r.refresh_from_db()
        assert r.status == Receipt.Status.ACCEPTED
        assert "приз" in r.moderator_comment.lower()

    def test_rejected_requires_comment(self):
        r = self._mk()
        resp = self.client.post(
            reverse("admin:lucky_receipt_receipt_change", args=[r.id]),
            {
                "user": self.user.id,
                "fn": r.fn, "fd": r.fd, "fp": r.fp,
                "purchased_at_0": r.purchased_at.strftime("%Y-%m-%d"),
                "purchased_at_1": r.purchased_at.strftime("%H:%M:%S"),
                "amount": "1500",
                "status": Receipt.Status.REJECTED,
                "moderator_comment": "",
            },
        )
        assert resp.status_code == 200
        r.refresh_from_db()
        assert r.status == Receipt.Status.PENDING

    def test_export_accepted_csv(self):
        accepted = self._mk(status=Receipt.Status.ACCEPTED, fn="10", fd="10", fp="10")
        pending = self._mk(status=Receipt.Status.PENDING, fn="20", fd="20", fp="20")

        resp = self.client.post(
            reverse("admin:lucky_receipt_receipt_changelist"),
            {
                "action": "export_accepted_csv",
                "_selected_action": [str(accepted.id), str(pending.id)],
            },
        )
        assert isinstance(resp, HttpResponse)
        assert resp.status_code == 200
        assert resp["Content-Type"].startswith("text/csv")

        body = resp.content.decode("utf-8-sig")
        rows = [row for row in body.splitlines() if row.strip()]

        assert len(rows) == 2

        cells = rows[1].split(";")
        assert cells[3] == "10"
