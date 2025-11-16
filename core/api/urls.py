from django.urls import path, include
from core.api.views import InvoiceToPendingProductsAPIView

urlpatterns = [
    path("products/pending/create/", InvoiceToPendingProductsAPIView.as_view(), name="pending-product-create"),
]