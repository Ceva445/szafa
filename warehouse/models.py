from django.db import models
from core.models import Product


class WarehouseStock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=20, blank=True, null=True)
    quantity = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["product", "size"]
        verbose_name = "Warehouse Stock"
        verbose_name_plural = "Warehouse Stocks"

    def __str__(self):
        return f"{self.product} - {self.size}: {self.quantity}"

    @property
    def total_value(self):
        return self.quantity * self.product.unit_price

    def update_stock(self, quantity_change):
        """Updates the quantity of goods in stock"""
        self.quantity += quantity_change
        if self.quantity < 0:
            self.quantity = 0
        self.save()


class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ("in", "Przyjęcie"),
        ("out", "Wydanie"),
        ("adjustment", "Korekta"),
        ("return", "Zwrot"),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=20, blank=True, null=True)
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()
    document_type = models.CharField(max_length=50)
    document_id = models.IntegerField()
    movement_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-movement_date"]

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product}"
