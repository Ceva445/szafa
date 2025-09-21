from django.db import models


class Company(models.Model):
    # Stores company names (Ceva-Piątek, Ceva-Stryków, Ceva Directed)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Department(models.Model):
    # Stores department names (STOCK, XDOCK, ECOM)
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Position(models.Model):
    # Stores position titles (specialist, magazynier, etc.)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Supplier(models.Model):
    # Stores supplier names (Firma 1, Firma 2, Firma 3)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class ProductCategory(models.Model):
    # Categorizes products by type (footwear, clothing, BHP) with unique names
    CATEGORY_TYPES = [
        ("footwear", "Obuwie"),
        ("clothing", "Odzież"),
        ("bhp", "Środki BHP"),
    ]

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=CATEGORY_TYPES)

    class Meta:
        unique_together = ["name", "type"]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class Product(models.Model):
    # Stores product details including code, name, category, size, price, usage period, and description
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT)
    size = models.CharField(max_length=20, blank=True, null=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    period_days = models.IntegerField(help_text="Okres użytkowania w dniach")
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.code} - {self.name}"
