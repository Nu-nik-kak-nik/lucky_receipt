from django.urls import path

from . import views

app_name = "receipts"

urlpatterns = [
    path("", views.IndexRedirectView.as_view(), name="index"),
    path("receipts/", views.ReceiptListView.as_view(), name="list"),
    path("receipts/new/", views.ReceiptCreateView.as_view(), name="create"),
    path("api/receipts/", views.ReceiptListAPIView.as_view(), name="api_list"),
]
