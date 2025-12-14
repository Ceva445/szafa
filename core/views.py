from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages

from core.utils import replace_pending_products_safe
from .models import Company, Department, PendingProduct, Position, ProductCategory, Supplier, Product
from .forms import (
    CompanyForm,
    DepartmentForm,
    PositionForm,
    ProductCategoryForm,
    SupplierForm,
    ProductForm,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from szafa import settings
import requests

#Invoice Analyze View
class InvoiceAnalyzeView(LoginRequiredMixin, View):
    template_name = "core/invoice_analyze.html"

    def get(self, request, *args, **kwargs):
        # Відображаємо форму
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        file = request.FILES.get("file")
        doc_type = request.POST.get("doc_type")
        forward_url_map = {
            "extract_fv": "/core/api/products/pending/create/",
            "extract_wz": "/documents/api/documents/pending/create/",
        }

        if file and doc_type:
            path = default_storage.save(f"uploads/{file.name}", ContentFile(file.read()))
            file_url = settings.HOSTING_URL + default_storage.url(path)

            payload = {
                "doc_type": doc_type,
                "file_url": file_url,
                "forward_url": settings.HOSTING_URL + forward_url_map.get(doc_type, "/"),
                "wait_response": False, # додати конфігурацію
            }
            print("Payload:", payload)

            try:
                response = requests.post(settings.LUSTRO_URL, json=payload)
                response.raise_for_status()
                return redirect("core:invoice_analyze")
            except Exception as e:
                return render(request, self.template_name, {"error": str(e)})

        return render(request, self.template_name, {"error": "Brak pliku lub typu faktury"})
    
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


class PendingProductListView(View):
    template_name = "core/pending_products_list.html"

    def get(self, request):
        objects = PendingProduct.objects.order_by("-created_at")
        categories = ProductCategory.objects.all()
        return render(request, self.template_name, {
            "objects": objects,
            "categories": categories,
        })

    def post(self, request):
        action = request.POST.get("action")
        ids = request.POST.getlist("selected")

        if not ids:
            messages.warning(request, "Nie wybrano żadnych pozycji.")
            return redirect("core:pending_list")

        qs = PendingProduct.objects.filter(id__in=ids)

        if action == "approve":
            items = list(qs)
            new_products = []

            for item in items:
                new_products.append(Product(
                    code=request.POST.get(f"code_{item.id}"),
                    name=request.POST.get(f"name_{item.id}"),
                    size=request.POST.get(f"size_{item.id}"),
                    unit_price=request.POST.get(f"price_{item.id}"),
                    period_days=request.POST.get(f"period_{item.id}"),
                    min_qty_on_stock=request.POST.get(f"minqty_{item.id}"),
                    category_id=request.POST.get(f"category_{item.id}"),
                    description=item.description,
                ))

            Product.objects.bulk_create(new_products)
            replace_pending_products_safe()
            qs.delete()

            messages.success(request, f"Zatwierdzono {len(new_products)} produktów.")
            return redirect("core:pending_list")

        if action == "delete":
            count = qs.count()
            replace_pending_products_safe()
            qs.delete()
            messages.success(request, f"Usunięto {count} pozycji.")
            return redirect("core:pending_list")

        messages.error(request, "Nieznana akcja.")
        return redirect("core:pending_list")


class PendingProductApproveView(View):
    def post(self, request, pk):
        item = get_object_or_404(PendingProduct, pk=pk)
        Product.objects.create(
            code=item.code,
            name=item.name,
            category=item.category,
            size=item.size,
            unit_price=item.unit_price,
            min_qty_on_stock=item.min_qty_on_stock,
            period_days=item.period_days,
            description=item.description,
        )
        replace_pending_products_safe()
        item.delete()
        messages.success(request, f"Produkt {item.code} został zatwierdzony.")
        return redirect("core:pending_list")
    

class PendingProductDeleteView(View):
    def post(self, request, pk):
        replace_pending_products_safe()
        item = get_object_or_404(PendingProduct, pk=pk)
        item.delete()
        messages.success(request, "Usunięto rekord.")
        return redirect("core:pending_list")


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
