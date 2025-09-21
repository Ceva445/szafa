from django.contrib import admin
from .models import WarehouseStock, StockMovement


@admin.register(WarehouseStock)
class WarehouseStockAdmin(admin.ModelAdmin):
    list_display = ["product", "size", "quantity", "total_value", "last_updated"]
    list_filter = ["product__category"]
    search_fields = ["product__code", "product__name"]
    readonly_fields = ["total_value", "last_updated"]
    list_editable = ["quantity"]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "size",
        "movement_type",
        "quantity",
        "document_type",
        "movement_date",
    ]
    list_filter = ["movement_type", "movement_date"]
    search_fields = ["product__code", "product__name", "document_type"]
    readonly_fields = ["movement_date"]
    date_hierarchy = "movement_date"
