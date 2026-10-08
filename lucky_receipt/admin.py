import csv

from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse

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
    list_select_related = ("user",)

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

    actions = ["mark_accepted", "mark_rejected", "export_accepted_csv"]

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

    @admin.action(description="Экспортировать принятые чеки в CSV")
    def export_accepted_csv(self, request, queryset):
        accepted = queryset.filter(status=Receipt.Status.ACCEPTED).select_related("user")
        if not accepted.exists():
            self.message_user(
                request,
                "Среди выбранных нет принятых чеков",
                messages.WARNING,
            )
            return None

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="accepted_receipts.csv"'
        response.write("\ufeff")  # BOM для Excel

        writer = csv.writer(response, delimiter=";")
        writer.writerow([
            "ID", "Пользователь", "Email", "ФН", "ФД", "ФП",
            "Дата покупки", "Сумма", "Дата регистрации",
        ])
        for r in accepted:
            writer.writerow([
                r.id,
                r.user.username,
                r.user.email,
                r.fn,
                r.fd,
                r.fp,
                r.purchased_at.strftime("%d.%m.%Y %H:%M"),
                f"{r.amount:.2f}",
                r.created_at.strftime("%d.%m.%Y %H:%M"),
            ])
        return response
