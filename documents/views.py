from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.urls import reverse
from django.db import transaction
from django.contrib import messages
from django.db.models import Q, Prefetch
from datetime import datetime, date

from .models import IssueDocument, ReceiptDocument, DocumentItem, ReceiptItem
from core.models import Product, Supplier, Company
from employees.models import Employee


DATE_FMT = "%Y-%m-%d"


def parse_date_or_none(val):
    val = (val or "").strip()
    if not val:
        return None
    try:
        return datetime.strptime(val, DATE_FMT).date()
    except ValueError:
        return None


# =====================================================
# =============== DETAIL VIEWS ========================
# =====================================================

class DWDetailView(View):
    """Show details of DW (IssueDocument)"""

    def get(self, request, pk):
        doc = get_object_or_404(IssueDocument, pk=pk)
        items = doc.items.select_related("product").all()
        context = {
            "doc": doc,
            "items": items,
            "active": "documents_dw",
            "doc_type": "DW",
        }
        return render(request, "documents/detail_dw.html", context)


class PZDetailView(View):
    """Show details of PZ (ReceiptDocument)"""

    def get(self, request, pk):
        doc = get_object_or_404(ReceiptDocument, pk=pk)
        items = doc.items.select_related("product").all()
        context = {
            "doc": doc,
            "items": items,
            "active": "documents_pz",
            "doc_type": "PZ",
        }
        return render(request, "documents/detail_pz.html", context)


# =====================================================
# =============== CREATE VIEWS ========================
# =====================================================

class IssueCreateView(View):
    """Create a DW (IssueDocument) — wydanie dla pracownika"""

    def get(self, request):
        context = {
            "employees": Employee.objects.select_related("position", "company").all(),
            "products": Product.objects.all(),
            "active": "documents_dw",
            "today": date.today().isoformat(),
        }
        return render(request, "documents/create_dw.html", context)

    def post(self, request):
        employee_id = request.POST.get("employee")
        issue_date = parse_date_or_none(request.POST.get("issue_date"))
        product_ids = request.POST.getlist("product_id[]")
        quantities = request.POST.getlist("quantity[]")
        sizes = request.POST.getlist("size[]")
        notes = request.POST.getlist("notes[]")

        errors = {}
        if not employee_id:
            errors["employee"] = "Wybierz pracownika"
        if not issue_date:
            errors["issue_date"] = "Podaj datę wystawienia"

        items_parsed = []
        for i, pid in enumerate(product_ids):
            pid = pid.strip()
            if not pid:
                continue
            try:
                qty = int(quantities[i])
            except Exception:
                errors[f"quantity_{i}"] = "Niepoprawna ilość"
                continue
            size = sizes[i].strip() if i < len(sizes) else ""
            note = notes[i].strip() if i < len(notes) else ""
            items_parsed.append((pid, qty, size, note))

        if not items_parsed:
            errors["items"] = "Dodaj przynajmniej jedną pozycję"

        if errors:
            context = {
                "employees": Employee.objects.all(),
                "products": Product.objects.all(),
                "errors": errors,
                "form": request.POST,
                "active": "documents_dw",
                "today": date.today().isoformat(),
            }
            return render(request, "documents/create_dw.html", context)

        try:
            with transaction.atomic():
                doc = IssueDocument.objects.create(
                    document_type="DW",
                    issue_date=issue_date,
                    employee_id=employee_id,
                )
                for pid, qty, size, note in items_parsed:
                    product = Product.objects.get(pk=pid)
                    DocumentItem.objects.create(
                        document=doc,
                        product=product,
                        quantity=qty,
                        size=size or None,
                        notes=note,
                    )
        except Exception as e:
            messages.error(request, f"Błąd zapisu: {e}")
            return render(
                request,
                "documents/create_dw.html",
                {
                    "employees": Employee.objects.all(),
                    "products": Product.objects.all(),
                    "errors": {"general": str(e)},
                    "form": request.POST,
                    "active": "documents_dw",
                    "today": date.today().isoformat(),
                },
            )

        messages.success(request, f"DW utworzone: {doc.document_number}")
        return redirect(reverse("documents:dw_detail", args=[doc.pk]))


class ReceiptCreateView(View):
    """Create a PZ (ReceiptDocument) — przyjęcie zewnętrzne"""

    def get(self, request):
        context = {
            "suppliers": Supplier.objects.all(),
            "companies": Company.objects.all(),
            "products": Product.objects.all(),
            "active": "documents_pz",
            "today": date.today().isoformat(),
        }
        return render(request, "documents/create_pz.html", context)

    def post(self, request):
        supplier_id = request.POST.get("supplier")
        recipient_id = request.POST.get("recipient")
        issue_date = parse_date_or_none(request.POST.get("issue_date"))
        product_ids = request.POST.getlist("product_id[]")
        quantities = request.POST.getlist("quantity[]")
        sizes = request.POST.getlist("size[]")
        unit_prices = request.POST.getlist("unit_price[]")
        notes = request.POST.getlist("notes[]")

        errors = {}
        if not supplier_id:
            errors["supplier"] = "Wybierz dostawcę"
        if not recipient_id:
            errors["recipient"] = "Wybierz odbiorcę"
        if not issue_date:
            errors["issue_date"] = "Podaj datę wystawienia"

        items_parsed = []
        for i, pid in enumerate(product_ids):
            pid = pid.strip()
            if not pid:
                continue
            try:
                qty = int(quantities[i])
            except Exception:
                errors[f"quantity_{i}"] = "Niepoprawna ilość"
                continue
            try:
                up = (
                    float(unit_prices[i])
                    if i < len(unit_prices) and unit_prices[i].strip()
                    else 0.0
                )
            except Exception:
                errors[f"unit_price_{i}"] = "Niepoprawna cena"
                continue
            size = sizes[i].strip() if i < len(sizes) else ""
            note = notes[i].strip() if i < len(notes) else ""
            items_parsed.append((pid, qty, size, up, note))

        if not items_parsed:
            errors["items"] = "Dodaj przynajmniej jedną pozycję"

        if errors:
            return render(
                request,
                "documents/create_pz.html",
                {
                    "suppliers": Supplier.objects.all(),
                    "companies": Company.objects.all(),
                    "products": Product.objects.all(),
                    "errors": errors,
                    "form": request.POST,
                    "active": "documents_pz",
                    "today": date.today().isoformat(),
                },
            )

        try:
            with transaction.atomic():
                doc = ReceiptDocument.objects.create(
                    document_type="PZ",
                    issue_date=issue_date,
                    supplier_id=supplier_id,
                    recipient_id=recipient_id,
                )
                for pid, qty, size, up, note in items_parsed:
                    product = Product.objects.get(pk=pid)
                    ReceiptItem.objects.create(
                        document=doc,
                        product=product,
                        quantity=qty,
                        size=size or None,
                        unit_price=up,
                        total_value=qty * up,
                        notes=note,
                    )
        except Exception as e:
            messages.error(request, f"Błąd zapisu: {e}")
            return render(
                request,
                "documents/create_pz.html",
                {
                    "suppliers": Supplier.objects.all(),
                    "companies": Company.objects.all(),
                    "products": Product.objects.all(),
                    "errors": {"general": str(e)},
                    "form": request.POST,
                    "active": "documents_pz",
                    "today": date.today().isoformat(),
                },
            )

        messages.success(request, f"PZ utworzone: {doc.document_number}")
        return redirect(reverse("documents:pz_detail", args=[doc.pk]))


# =====================================================
# =============== EDIT / ITEM VIEWS ===================
# =====================================================

class DocumentEditView(View):
    """Edit DW or PZ (basic fields only)"""

    def get(self, request, pk, kind):
        if kind == "dw":
            doc = get_object_or_404(IssueDocument, pk=pk)
            return render(
                request,
                "documents/edit_dw.html",
                {"doc": doc, "employees": Employee.objects.all(), "active": "documents_dw"},
            )
        else:
            doc = get_object_or_404(ReceiptDocument, pk=pk)
            return render(
                request,
                "documents/edit_pz.html",
                {
                    "doc": doc,
                    "suppliers": Supplier.objects.all(),
                    "companies": Company.objects.all(),
                    "active": "documents_pz",
                },
            )

    def post(self, request, pk, kind):
        issue_date = parse_date_or_none(request.POST.get("issue_date"))
        if not issue_date:
            messages.error(request, "Niepoprawna data")
            return redirect(request.path)

        if kind == "dw":
            doc = get_object_or_404(IssueDocument, pk=pk)
            emp_id = request.POST.get("employee")
            if not emp_id:
                messages.error(request, "Wybierz pracownika")
                return redirect(request.path)
            doc.issue_date = issue_date
            doc.employee_id = emp_id
            doc.save()
            messages.success(request, "DW zaktualizowane")
            return redirect(reverse("documents:dw_detail", args=[doc.pk]))
        else:
            doc = get_object_or_404(ReceiptDocument, pk=pk)
            supplier_id = request.POST.get("supplier")
            recipient_id = request.POST.get("recipient")
            if not supplier_id or not recipient_id:
                messages.error(request, "Wybierz dostawcę i odbiorcę")
                return redirect(request.path)
            doc.issue_date = issue_date
            doc.supplier_id = supplier_id
            doc.recipient_id = recipient_id
            doc.save()
            messages.success(request, "PZ zaktualizowane")
            return redirect(reverse("documents:pz_detail", args=[doc.pk]))


class ItemMarkUsedView(View):
    """Mark a DocumentItem as used (DW only)"""

    def post(self, request, item_id):
        it = get_object_or_404(DocumentItem, pk=item_id)
        it.mark_as_used()
        messages.success(request, "Pozycja oznaczona jako zużyta")
        return redirect(reverse("employees:detail", args=[it.document.employee_id]))


class ItemDeleteView(View):
    """Delete DW or PZ item"""

    def post(self, request, item_id, kind):
        if kind == "dw":
            it = get_object_or_404(DocumentItem, pk=item_id)
            parent = it.document
            it.delete()
            messages.success(request, "Pozycja usunięta")
            return redirect(reverse("documents:dw_detail", args=[parent.pk]))
        else:
            it = get_object_or_404(ReceiptItem, pk=item_id)
            parent = it.document
            it.delete()
            messages.success(request, "Pozycja usunięta")
            return redirect(reverse("documents:pz_detail", args=[parent.pk]))


# =====================================================
# =============== LIST VIEWS ==========================
# =====================================================

class DWListView(View):
    """List DW (IssueDocument) documents"""

    def get(self, request):
        q = request.GET.get("q", "").strip()
        company_id = request.GET.get("company")

        qs = IssueDocument.objects.select_related(
            "employee", "employee__company"
        ).prefetch_related(
            Prefetch("items", queryset=DocumentItem.objects.select_related("product"))
        )

        if q:
            qs = qs.filter(
                Q(document_number__icontains=q)
                | Q(employee__first_name__icontains=q)
                | Q(employee__last_name__icontains=q)
                | Q(employee__company__name__icontains=q)
            )

        if company_id:
            qs = qs.filter(employee__company_id=company_id)

        context = {
            "documents": qs.order_by("-issue_date"),
            "q": q,
            "company": company_id,
            "companies": Company.objects.all().order_by("name"),
            "active": "documents_dw",
            "doc_type": "DW",
        }
        return render(request, "documents/list_dw.html", context)


class PZListView(View):
    """List PZ (ReceiptDocument) documents"""

    def get(self, request):
        q = request.GET.get("q", "").strip()
        supplier_id = request.GET.get("supplier")
        recipient_id = request.GET.get("recipient")

        qs = ReceiptDocument.objects.select_related(
            "supplier", "recipient"
        ).prefetch_related(
            Prefetch("items", queryset=ReceiptItem.objects.select_related("product"))
        )

        if q:
            qs = qs.filter(
                Q(document_number__icontains=q)
                | Q(supplier__name__icontains=q)
                | Q(recipient__name__icontains=q)
            )

        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        if recipient_id:
            qs = qs.filter(recipient_id=recipient_id)

        context = {
            "documents": qs.order_by("-issue_date"),
            "q": q,
            "supplier": supplier_id,
            "recipient": recipient_id,
            "suppliers": Supplier.objects.all().order_by("name"),
            "recipients": Company.objects.all().order_by("name"),
            "active": "documents_pz",
            "doc_type": "PZ",
        }
        return render(request, "documents/list_pz.html", context)
