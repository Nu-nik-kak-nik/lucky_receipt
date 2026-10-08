from django import forms
from django.contrib import admin

from .models import Receipt


class ReceiptAdminForm(forms.ModelForm):
    class Meta:
        model = Receipt
        fields = "__all__"

    def clean(self):
        data = super().clean()
        status = data.get("status")
        reason = (data.get("rejection_reason") or "").strip()

        if status == Receipt.Status.REJECTED and not reason:
            self.add_error("rejection_reason", "Причина отказа обязательна")

        if status != Receipt.Status.REJECTED:
            data["rejection_reason"] = ""

        return data


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    form = ReceiptAdminForm

    list_display = (
        "id",
        "user",
        "purchased_at",
        "amount",
        "status",
        "created_at",
    )
    list_filter = ("status", "purchased_at", "created_at")
    search_fields = ("fn", "fd", "fp", "user__username", "user__email")
    date_hierarchy = "purchased_at"
    ordering = ("-created_at",)
    list_per_page = 25

    readonly_fields = (
        "user",
        "fn",
        "fd",
        "fp",
        "purchased_at",
        "amount",
        "created_at",
    )

    fieldsets = (
        ("Реквизиты чека", {
            "fields": ("user", "fn", "fd", "fp", "purchased_at", "amount", "created_at"),
        }),
        ("Модерация", {
            "fields": ("status", "rejection_reason"),
        }),
    )

    actions = ["mark_accepted", "mark_rejected"]

    @admin.action(description="Принять выбранные чеки")
    def mark_accepted(self, request, queryset):
        updated = queryset.update(
            status=Receipt.Status.ACCEPTED,
            rejection_reason="",
        )
        self.message_user(request, f"Принято чеков: {updated}")

    @admin.action(description="Отправить на повторную проверку")
    def mark_pending(self, request, queryset):
        updated = queryset.update(
            status=Receipt.Status.PENDING,
            rejection_reason="",
        )
        self.message_user(request, f"Возвращено на проверку: {updated}")
