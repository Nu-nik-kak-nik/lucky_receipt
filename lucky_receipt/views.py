from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView

from .forms import ReceiptForm
from .models import Receipt


def _form_errors_to_json(form) -> dict:
    out: dict[str, list[str]] = {}
    for field, errors in form.errors.get_json_data().items():
        out[field] = [e["message"] for e in errors]
    return out


def _wants_json(request) -> bool:
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return True
    accept = request.headers.get("accept", "")
    return "application/json" in accept


class IndexRedirectView(LoginRequiredMixin, View):
    def get(self, request):
        return redirect("receipts:list")


class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        messages.success(self.request, "Регистрация завершена. Теперь войдите.")
        return super().form_valid(form)


class ReceiptListView(LoginRequiredMixin, ListView):
    model = Receipt
    template_name = "receipts/receipt_list.html"
    context_object_name = "receipts"
    paginate_by = 10

    def get_queryset(self):
        return (
            Receipt.objects
            .filter(user=self.request.user)
            .order_by("-purchased_at", "-id")
        )


class ReceiptCreateView(LoginRequiredMixin, View):
    template_name = "receipts/receipt_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": ReceiptForm()})

    def post(self, request):
        form = ReceiptForm(request.POST)
        wants_json = _wants_json(request)

        if form.is_valid():
            receipt: Receipt = form.save(commit=False)
            receipt.user = request.user
            receipt.status = Receipt.Status.PENDING

            try:
                receipt.save()
            except IntegrityError:
                message = "Чек с такими ФН, ФД и ФП уже зарегистрирован"
                if wants_json:
                    return JsonResponse(
                        {"ok": False, "errors": {"__all__": [message]}},
                        status=400,
                    )
                form.add_error(None, message)
            else:
                if wants_json:
                    return JsonResponse({
                        "ok": True,
                        "receipt": {
                            "id": receipt.id,
                            "status": receipt.status,
                            "status_display": receipt.get_status_display(),
                            "created_at": receipt.created_at.isoformat(),
                        },
                        "redirect_url": reverse("receipts:list"),
                    })
                messages.success(
                    request,
                    "Чек зарегистрирован и отправлен на проверку",
                )
                return redirect("receipts:list")

        if wants_json:
            return JsonResponse(
                {"ok": False, "errors": _form_errors_to_json(form)},
                status=400,
            )

        return render(request, self.template_name, {"form": form})


class ReceiptListAPIView(LoginRequiredMixin, View):
    def get(self, request):
        qs = (
            Receipt.objects
            .filter(user=request.user)
            .order_by("-purchased_at", "-id")
        )
        results = [
            {
                "id": r.id,
                "fn": r.fn,
                "fd": r.fd,
                "fp": r.fp,
                "purchased_at": r.purchased_at.isoformat(),
                "amount": str(r.amount),
                "status": r.status,
                "status_display": r.get_status_display(),
                "rejection_reason": r.rejection_reason,
                "created_at": r.created_at.isoformat(),
            }
            for r in qs
        ]
        return JsonResponse({"results": results})
