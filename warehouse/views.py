from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.db.models import Q
from django.urls import reverse
from .models import WarehouseStock, StockMovement
from core.models import Product
from django.core.paginator import Paginator

DATE_FMT = "%Y-%m-%d"

class WarehouseListView(View):
    """
    List current warehouse stocks.
    Supports:
      - search by product code, product name, size
      - toggle show_zero via GET param show_zero=1
      - optional filter by company/recipient (if needed later)
    """
    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        show_zero = request.GET.get("show_zero") == "1"

        qs = WarehouseStock.objects.select_related("product").all()

        if q:
            qs = qs.filter(
                Q(product__code__icontains=q)
                | Q(product__name__icontains=q)
                | Q(size__icontains=q)
            )

        if not show_zero:
            qs = qs.filter(quantity__gt=0)

        # simple pagination
        paginator = Paginator(qs.order_by("product__code", "size"), 50)
        page = request.GET.get("page", 1)
        stocks = paginator.get_page(page)

        context = {
            "stocks": stocks,
            "q": q,
            "show_zero": show_zero,
            "active": "warehouse",
        }
        return render(request, "warehouse/list.html", context)


class WarehouseDetailView(View):
    """
    Detail for a single WarehouseStock record.
    Shows product, size, current quantity, value and quick actions.
    """
    def get(self, request, pk):
        ws = get_object_or_404(WarehouseStock.objects.select_related("product"), pk=pk)
        movements = StockMovement.objects.filter(product=ws.product, size=ws.size).order_by("-movement_date")[:200]

        context = {
            "stock": ws,
            "movements": movements,
            "active": "warehouse",
        }
        return render(request, "warehouse/detail.html", context)


class StockHistoryView(View):
    """
    Dedicated view to show paginated history for a product/size.
    Accepts GET params product_id and size; or pk of WarehouseStock.
    """
    def get(self, request, pk=None):
        # if pk provided, use warehouse stock
        if pk:
            ws = get_object_or_404(WarehouseStock.objects.select_related("product"), pk=pk)
            product = ws.product
            size = ws.size
        else:
            pid = request.GET.get("product_id")
            size = request.GET.get("size")
            product = get_object_or_404(Product, pk=pid)

        qs = StockMovement.objects.filter(product=product)
        if size:
            qs = qs.filter(size=size)
        qs = qs.order_by("-movement_date")

        paginator = Paginator(qs, 50)
        page = request.GET.get("page", 1)
        movements = paginator.get_page(page)

        context = {
            "product": product,
            "size": size,
            "movements": movements,
            "active": "warehouse",
        }
        return render(request, "warehouse/history.html", context)
