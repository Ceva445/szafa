# core/forms.py
from django import forms
from .models import Company, Department, Position, ProductCategory, Supplier, Product


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ["name"]


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name"]


class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ["name"]


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name"]


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "code",
            "name",
            "category",
            "size",
            "unit_price",
            "period_days",
            "min_qty_on_stock",
            "description",
        ]


class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ["name", "type"]