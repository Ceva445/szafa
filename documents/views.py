from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.urls import reverse
from django.db import transaction
from django.contrib import messages
from django.db.models import Q, Prefetch
from datetime import datetime, date, timedelta

from .models import (
    IssueDocument,
    ReceiptDocument,
    DocumentItem,
    ReceiptItem,
)
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


class DocumentsListView(View):
    """
    List documents (both PZ and DW). Supports:
    - filter by type (DW/PZ/all)
    - search by columns (document_number, employee last name for DW, supplier name for PZ)
    - filter by company/recipient
    """

    def get(self, request):
        doc_type = request.GET.get("type", "")  # "DW", "PZ" or empty
        q = request.GET.get("q", "").strip()
        company_id = request.GET.get("company")
        supplier_id = request.GET.get("supplier")

        # Base querysets
        dw_qs = IssueDocument.objects.select_related("employee").prefetch_related(
            Prefetch("items", queryset=DocumentItem.objects.select_related("product"))
        )
        pz_qs = ReceiptDocument.objects.select_related(
            "supplier", "recipient"
        ).prefetch_related(
            Prefetch("items", queryset=ReceiptItem.objects.select_related("product"))
        )

        if doc_type == "DW":
            qs = dw_qs
        elif doc_type == "PZ":
            qs = pz_qs
        else:
            # combine into list for template convenience (sorted by date desc)
            qs = list(dw_qs) + list(pz_qs)
            qs = sorted(
                qs,
                key=lambda d: getattr(
                    d, "issue_date", getattr(d, "issue_date", date.min)
                ),
                reverse=True,
            )

        # apply filters/search for homogeneous querysets (DW or PZ)
        if doc_type == "DW" and q:
            qs = qs.filter(
                Q(document_number__icontains=q)
                | Q(employee__last_name__icontains=q)
                | Q(employee__first_name__icontains=q)
            )
        if doc_type == "PZ" and q:
            qs = qs.filter(document_number__icontains=q)

        if company_id:
            # company/recipient filter for PZ recipients
            qs = qs.filter(recipient_id=company_id) if doc_type == "PZ" else qs

        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id) if doc_type == "PZ" else qs

        context = {
            "documents": qs,
            "doc_type": doc_type,
            "companies": Company.objects.all(),
            "suppliers": Supplier.objects.all(),
            "active": "documents",
            "q": q,
        }
        return render(request, "documents/list.html", context)


class DocumentDetailView(View):
    """Show document detail (DW or PZ) with items and actions"""

    def get(self, request, pk, kind):
        # kind: 'dw' or 'pz'
        if kind == "dw":
            doc = get_object_or_404(IssueDocument, pk=pk)
            items = doc.items.select_related("product").all()

        else:
            doc = get_object_or_404(ReceiptDocument, pk=pk)
            items = doc.items.select_related("product").all()

        context = {
            "doc": doc,
            "items": items,
            "kind": kind,
            "active": "documents",
        }
        return render(request, "documents/detail.html", context)


class IssueCreateView(View):
    """Create a DW (IssueDocument) — wydanie dla pracownika"""

    def get(self, request):
        context = {
            "employees": Employee.objects.select_related("position", "company").all(),
            "products": Product.objects.all(),
            "active": "documents",
            "today": date.today().isoformat(),
        }
        return render(request, "documents/create_dw.html", context)

    def post(self, request):
        employee_id = request.POST.get("employee")
        issue_date = parse_date_or_none(request.POST.get("issue_date"))
        # items arrays
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
                "active": "documents",
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
            context = {
                "employees": Employee.objects.all(),
                "products": Product.objects.all(),
                "errors": {"general": str(e)},
                "form": request.POST,
                "active": "documents",
                "today": date.today().isoformat(),
            }
            return render(request, "documents/create_dw.html", context)

        messages.success(request, f"DW utworzone: {doc.document_number}")
        return redirect(reverse("documents:detail", args=[doc.pk, "dw"]))


class ReceiptCreateView(View):
    """Create a PZ (ReceiptDocument) — przyjęcie zewnętrzne"""

    def get(self, request):
        context = {
            "suppliers": Supplier.objects.all(),
            "companies": Company.objects.all(),
            "products": Product.objects.all(),
            "active": "documents",
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
            context = {
                "suppliers": Supplier.objects.all(),
                "companies": Company.objects.all(),
                "products": Product.objects.all(),
                "errors": errors,
                "form": request.POST,
                "active": "documents",
                "today": date.today().isoformat(),
            }
            return render(request, "documents/create_pz.html", context)

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
            context = {
                "suppliers": Supplier.objects.all(),
                "companies": Company.objects.all(),
                "products": Product.objects.all(),
                "errors": {"general": str(e)},
                "form": request.POST,
                "active": "documents",
                "today": date.today().isoformat(),
            }
            return render(request, "documents/create_pz.html", context)

        messages.success(request, f"PZ utworzone: {doc.document_number}")
        return redirect(reverse("documents:detail", args=[doc.pk, "pz"]))


class DocumentEditView(View):
    """Simple edit for basic fields (does not attempt to edit items here)"""

    def get(self, request, pk, kind):
        if kind == "dw":
            doc = get_object_or_404(IssueDocument, pk=pk)
            context = {
                "doc": doc,
                "employees": Employee.objects.all(),
                "active": "documents",
            }
            return render(request, "documents/edit_dw.html", context)
        else:
            doc = get_object_or_404(ReceiptDocument, pk=pk)
            context = {
                "doc": doc,
                "suppliers": Supplier.objects.all(),
                "companies": Company.objects.all(),
                "active": "documents",
            }
            return render(request, "documents/edit_pz.html", context)

    def post(self, request, pk, kind):
        # minimal editable fields (issue_date, linked fk)
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
            return redirect(reverse("documents:detail", args=[doc.pk, "dw"]))
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
            return redirect(reverse("documents:detail", args=[doc.pk, "pz"]))


class ItemMarkUsedView(View):
    """Mark a DocumentItem as used (moves to used)"""

    def post(self, request, item_id):
        it = get_object_or_404(DocumentItem, pk=item_id)
        it.mark_as_used()
        messages.success(request, "Pozycja oznaczona jako zużyta")
        return redirect(reverse("employees:detail", args=[it.document.employee_id]))


class ItemDeleteView(View):
    """Delete any item (DocumentItem or ReceiptItem)"""

    def post(self, request, item_id, kind):
        if kind == "dw":
            it = get_object_or_404(DocumentItem, pk=item_id)
            parent = it.document
            it.delete()
            messages.success(request, "Pozycja usunięta")
            return redirect(reverse("documents:detail", args=[parent.pk, "dw"]))
        else:
            it = get_object_or_404(ReceiptItem, pk=item_id)
            parent = it.document
            it.delete()
            messages.success(request, "Pozycja usunięta")
            return redirect(reverse("documents:detail", args=[parent.pk, "pz"]))
