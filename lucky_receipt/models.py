from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Receipt(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "На проверке"
        ACCEPTED = "accepted", "Принят"
        REJECTED = "rejected", "Отклонён"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="receipts",
        verbose_name="Пользователь",
    )
    fn = models.CharField("ФН", max_length=16)
    fd = models.CharField("ФД", max_length=20)
    fp = models.CharField("ФП", max_length=20)
    purchased_at = models.DateTimeField("Дата и время покупки")
    amount = models.DecimalField(
        "Сумма",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    status = models.CharField(
        "Статус",
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    rejection_reason = models.TextField("Причина отказа", blank=True)
    created_at = models.DateTimeField("Дата регистрации", auto_now_add=True)

    class Meta:
        verbose_name = "Чек"
        verbose_name_plural = "Чеки"
        ordering = ["-purchased_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["fn", "fd", "fp"],
                name="uniq_receipt_fn_fd_fp",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "-purchased_at"]),
        ]

    def __str__(self) -> str:
        return f"Чек {self.fn}/{self.fd}/{self.fp} от {self.purchased_at:%d.%m.%Y}"

    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING
