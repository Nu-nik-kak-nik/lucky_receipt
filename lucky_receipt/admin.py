import csv

from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html

from .models import Receipt, ReceiptPhoto


class ReceiptAdminForm(forms.ModelForm):
    class Meta:
        model = Receipt
        fields = "__all__"

    def clean(self):
        data = super().clean()
        status = data.get("status")
        comment = (data.get("moderator_comment") or "").strip()
        if status == Receipt.Status.REJECTED and not comment:
            self.add_error(
                "moderator_comment",
                "При отклонении обязательно укажите причину",
            )

        return data


class RejectWithCommentForm(forms.Form):
    comment = forms.CharField(
        label="Информация (причина отказа)",
        widget=forms.Textarea(attrs={"rows": 4, "cols": 60}),
        required=True,
    )


class ReceiptPhotoInline(admin.TabularInline):
    model = ReceiptPhoto
    extra = 0
    fields = ("image", "preview", "uploaded_at")
    readonly_fields = ("preview", "uploaded_at")

    @admin.display(description="Превью")
    def preview(self, obj):
        if not obj or not obj.image:
            return "—"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">'
            '<img src="{}" style="max-height:140px;border-radius:6px">'
            "</a>",
            obj.image.url,
            obj.image.url,
        )


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    form = ReceiptAdminForm

    list_display = ("id", "user", "purchased_at", "amount", "status", "created_at")
    list_filter = ("status", "purchased_at", "created_at")
    search_fields = ("fn", "fd", "fp", "user__username", "user__email")
    date_hierarchy = "purchased_at"
    ordering = ("-created_at",)
    list_per_page = 25
    list_select_related = ("user",)

    readonly_fields = ("user", "fn", "fd", "fp", "purchased_at", "amount", "created_at")

    fieldsets = (
        ("Реквизиты чека", {
            "fields": ("user", "fn", "fd", "fp", "purchased_at", "amount", "created_at"),
        }),
        ("Модерация", {
            "fields": ("status", "moderator_comment"),
            "description": (
                "Комментарий обязателен при отклонении. "
                "При принятии можно оставить пояснение для пользователя."
            ),
        }),
    )

    inlines = [ReceiptPhotoInline]

    actions = [
        "mark_accepted",
        "mark_won",
        "mark_pending",
        "reject_with_comment",
        "export_accepted_csv",
    ]

    @admin.action(description="Принять выбранные чеки")
    def mark_accepted(self, request, queryset):
        updated = queryset.update(status=Receipt.Status.ACCEPTED)
        self.message_user(request, f"Принято чеков: {updated}", messages.SUCCESS)

    @admin.action(description="Вернуть на проверку")
    def mark_pending(self, request, queryset):
        updated = queryset.update(status=Receipt.Status.PENDING)
        self.message_user(request, f"Возвращено на проверку: {updated}", messages.SUCCESS)

    @admin.action(description="Отклонить с указанием причины…")
    def reject_with_comment(self, request, queryset):
        ids = ",".join(str(pk) for pk in queryset.values_list("id", flat=True))
        url = reverse("admin:lucky_receipt_receipt_reject_with_comment")
        return HttpResponseRedirect(f"{url}?ids={ids}")

    @admin.action(description="Отметить как победителя")
    def mark_won(self, request, queryset):
        updated = queryset.update(status=Receipt.Status.WON)
        self.message_user(request, f"Отмечено победителями: {updated}", messages.SUCCESS)

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
        response.write("\ufeff")

        writer = csv.writer(response, delimiter=";")
        writer.writerow([
            "ID", "Пользователь", "Email", "ФН", "ФД", "ФП",
            "Дата покупки", "Сумма", "Дата регистрации", "Информация",
        ])
        for r in accepted:
            writer.writerow([
                r.id, r.user.username, r.user.email,
                r.fn, r.fd, r.fp,
                r.purchased_at.strftime("%d.%m.%Y %H:%M"),
                f"{r.amount:.2f}",
                r.created_at.strftime("%d.%m.%Y %H:%M"),
                r.moderator_comment.replace("\n", " "),
            ])
        return response

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "reject-with-comment/",
                self.admin_site.admin_view(self.reject_with_comment_view),
                name="lucky_receipt_receipt_reject_with_comment",
            ),
        ]
        return custom + urls

    def reject_with_comment_view(self, request):
        ids_param = request.GET.get("ids") or request.POST.get("ids") or ""
        try:
            ids = [int(x) for x in ids_param.split(",") if x.strip()]
        except ValueError:
            ids = []

        queryset = Receipt.objects.filter(pk__in=ids).select_related("user")
        if not queryset.exists():
            self.message_user(request, "Чеки не найдены", messages.ERROR)
            return HttpResponseRedirect(reverse("admin:lucky_receipt_receipt_changelist"))

        if request.method == "POST":
            form = RejectWithCommentForm(request.POST)
            if form.is_valid():
                comment = form.cleaned_data["comment"].strip()
                updated = queryset.update(
                    status=Receipt.Status.REJECTED,
                    moderator_comment=comment,
                )
                self.message_user(request, f"Отклонено чеков: {updated}", messages.SUCCESS)
                return HttpResponseRedirect(
                    reverse("admin:lucky_receipt_receipt_changelist")
                )
        else:
            form = RejectWithCommentForm()

        context = {
            **self.admin_site.each_context(request),
            "title": "Отклонить чеки с указанием причины",
            "form": form,
            "ids": ids_param,
            "receipts": queryset,
            "opts": self.model._meta,
        }
        return render(request, "admin/lucky_receipt/reject_with_comment.html", context)
