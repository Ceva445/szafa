from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from .models import Company, Department, Position, ProductCategory, Supplier, Product
from .forms import (
    CompanyForm,
    DepartmentForm,
    PositionForm,
    ProductCategoryForm,
    SupplierForm,
    ProductForm,
)
from django.contrib.auth.mixins import LoginRequiredMixin


# --- reusable base classes ---
class BaseListView(LoginRequiredMixin, View):
    model = None
    template_name = "core/list.html"
    context_object_name = "objects"
    active = "system"  # for base.html active menu

    def get_queryset(self):
        return self.model.objects.all().order_by("id")

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        ctx = {
            "objects": qs,
            "model_name": self.model._meta.model_name,
            "model_verbose": getattr(
                self.model._meta, "verbose_name_plural", self.model.__name__ + "s"
            ).title(),
            "active": self.active,
            "add_url": reverse(f"core:{self.model._meta.model_name}_add"),
        }
        return render(request, self.template_name, ctx)


class BaseCreateView(LoginRequiredMixin, View):
    model = None
    form_class = None
    template_name = "core/form.html"
    success_url_name = None
    active = "system"

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        ctx = {
            "form": form,
            "active": self.active,
            "creating": True,
            "model_name": self.model._meta.model_name,
            "cancel_url": reverse(f"core:{self.model._meta.model_name}_list"),
        }
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"{self.model.__name__} zapisano.")
            return redirect(reverse(self.success_url_name))
        ctx = {
            "form": form,
            "active": self.active,
            "creating": True,
            "model_name": self.model._meta.model_name,
            "cancel_url": reverse(f"core:{self.model._meta.model_name}_list"),
        }
        return render(request, self.template_name, ctx)


class BaseUpdateView(LoginRequiredMixin, View):
    model = None
    form_class = None
    template_name = "core/form.html"
    success_url_name = None
    active = "system"

    def get_object(self, pk):
        return get_object_or_404(self.model, pk=pk)

    def get(self, request, pk, *args, **kwargs):
        obj = self.get_object(pk)
        form = self.form_class(instance=obj)
        ctx = {
            "form": form,
            "object": obj,
            "active": self.active,
            "creating": False,
            "model_name": self.model._meta.model_name,
            "cancel_url": reverse(f"core:{self.model._meta.model_name}_list"),
        }
        return render(request, self.template_name, ctx)

    def post(self, request, pk, *args, **kwargs):
        obj = self.get_object(pk)
        form = self.form_class(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"{self.model.__name__} zaktualizowano.")
            return redirect(reverse(self.success_url_name))
        ctx = {
            "form": form,
            "object": obj,
            "active": self.active,
            "creating": False,
            "model_name": self.model._meta.model_name,
            "cancel_url": reverse(f"core:{self.model._meta.model_name}_list"),
        }
        return render(request, self.template_name, ctx)


class BaseDeleteView(LoginRequiredMixin, View):
    model = None
    template_name = "core/confirm_delete.html"
    success_url_name = None
    active = "system"

    def get_object(self, pk):
        return get_object_or_404(self.model, pk=pk)

    def get(self, request, pk, *args, **kwargs):
        obj = self.get_object(pk)
        ctx = {
            "object": obj,
            "active": self.active,
            "list_url": reverse(f"core:{self.model._meta.model_name}_list"),
        }
        return render(request, self.template_name, ctx)

    def post(self, request, pk, *args, **kwargs):
        obj = self.get_object(pk)
        obj.delete()
        messages.success(request, f"{self.model.__name__} usunięto.")
        return redirect(reverse(self.success_url_name))


# --- Конкретні view'и для Company (аналоги для інших моделей) ---


class CompanyListView(BaseListView):
    model = Company
    active = "system"


class CompanyCreateView(BaseCreateView):
    model = Company
    form_class = CompanyForm
    success_url_name = "core:company_list"
    active = "system"


class CompanyUpdateView(BaseUpdateView):
    model = Company
    form_class = CompanyForm
    success_url_name = "core:company_list"
    active = "system"


class CompanyDeleteView(BaseDeleteView):
    model = Company
    success_url_name = "core:company_list"
    active = "system"


# --- Department ---
class DepartmentListView(BaseListView):
    model = Department
    active = "system"


class DepartmentCreateView(BaseCreateView):
    model = Department
    form_class = DepartmentForm
    success_url_name = "core:department_list"
    active = "system"


class DepartmentUpdateView(BaseUpdateView):
    model = Department
    form_class = DepartmentForm
    success_url_name = "core:department_list"
    active = "system"


class DepartmentDeleteView(BaseDeleteView):
    model = Department
    success_url_name = "core:department_list"
    active = "system"


# --- Position ---
class PositionListView(BaseListView):
    model = Position


class PositionCreateView(BaseCreateView):
    model = Position
    form_class = PositionForm
    success_url_name = "core:position_list"


class PositionUpdateView(BaseUpdateView):
    model = Position
    form_class = PositionForm
    success_url_name = "core:position_list"


class PositionDeleteView(BaseDeleteView):
    model = Position
    success_url_name = "core:position_list"


# --- Supplier ---
class SupplierListView(BaseListView):
    model = Supplier


class SupplierCreateView(BaseCreateView):
    model = Supplier
    form_class = SupplierForm
    success_url_name = "core:supplier_list"


class SupplierUpdateView(BaseUpdateView):
    model = Supplier
    form_class = SupplierForm
    success_url_name = "core:supplier_list"


class SupplierDeleteView(BaseDeleteView):
    model = Supplier
    success_url_name = "core:supplier_list"


# --- Product ---
class ProductListView(BaseListView):
    model = Product
    template_name = "core/product_list.html"


class ProductCreateView(BaseCreateView):
    model = Product
    form_class = ProductForm
    success_url_name = "core:product_list"


class ProductUpdateView(BaseUpdateView):
    model = Product
    form_class = ProductForm
    success_url_name = "core:product_list"


class ProductDuplicateView(LoginRequiredMixin, View):
    template_name = "core/form.html"
    form_class = ProductForm
    model = Product
    active = "system"

    def get(self, request, pk, *args, **kwargs):
        original = get_object_or_404(Product, pk=pk)

        form = self.form_class(instance=original)

        form.initial["code"] = f"{original.code}_COPY"

        ctx = {
            "form": form,
            "active": self.active,
            "creating": True,
            "model_name": self.model._meta.model_name,
            "cancel_url": reverse(f"core:{self.model._meta.model_name}_list"),
        }
        return render(request, self.template_name, ctx)

    def post(self, request, pk, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            new_product = form.save()
            messages.success(request, "Duplikat produktu został utworzony.")
            return redirect(reverse("core:product_list"))

        ctx = {
            "form": form,
            "active": self.active,
            "creating": True,
            "model_name": self.model._meta.model_name,
            "cancel_url": reverse(f"core:{self.model._meta.model_name}_list"),
        }
        return render(request, self.template_name, ctx)


class ProductDeleteView(BaseDeleteView):
    model = Product
    success_url_name = "core:product_list"


# --- ProductCategory ---
class ProductCategoryListView(BaseListView):
    model = ProductCategory
    active = "system"


class ProductCategoryCreateView(BaseCreateView):
    model = ProductCategory
    form_class = ProductCategoryForm
    success_url_name = "core:productcategory_list"
    active = "system"


class ProductCategoryUpdateView(BaseUpdateView):
    model = ProductCategory
    form_class = ProductCategoryForm
    success_url_name = "core:productcategory_list"
    active = "system"


class ProductCategoryDeleteView(BaseDeleteView):
    model = ProductCategory
    success_url_name = "core:productcategory_list"
    active = "system"
