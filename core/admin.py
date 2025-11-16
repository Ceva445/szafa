from django.contrib import admin
from .models import Company, Department, Position, Supplier, ProductCategory, Product, PendingProduct


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "type"]
    list_filter = ["type"]
    search_fields = ["name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "category", "size", "unit_price", "period_days"]
    list_filter = ["category", "category__type"]
    search_fields = ["code", "name"]
    list_editable = ["unit_price", "period_days"]


@admin.register(PendingProduct)
class PendingProductAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "category", "size", "unit_price", "description"]
    list_filter = ["category", "category__type"]
    search_fields = ["code", "name"]