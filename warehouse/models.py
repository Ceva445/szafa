from django.db import models
from core.models import Product

class WarehouseStock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=20, blank=True, null=True)
    quantity = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['product', 'size']
    
    def __str__(self):
        return f"{self.product} - {self.size}: {self.quantity}"
    
    @property
    def total_value(self):
        return self.quantity * self.product.unit_price

class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('in', 'Przyjęcie'),
        ('out', 'Wydanie'),
        ('adjustment', 'Korekta'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=20, blank=True, null=True)
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()
    document_type = models.CharField(max_length=50)
    document_id = models.IntegerField()
    movement_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product}"