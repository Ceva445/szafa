from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.urls import reverse
from django.db import transaction
from django.contrib import messages
from django.db.models import Q, Prefetch
from datetime import datetime, date

from .models import IssueDocument, PendingReceiptDocument, PendingReceiptItem, ReceiptDocument, DocumentItem, ReceiptItem
from core.models import Product, Supplier, Company
from employees.models import Employee
from django.contrib.auth.mixins import LoginRequiredMixin


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

class DWDetailView(LoginRequiredMixin, View):
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


class PZDetailView(LoginRequiredMixin, View):
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

class IssueCreateView(LoginRequiredMixin, View):
    """Create a DW (IssueDocument) — wydanie dla pracownika"""

    def get(self, request):
        employee_id = request.GET.get("employee")
        context = {
            "employees": Employee.objects.select_related("position", "company").all(),
            "products": Product.objects.filter(warehousestock__quantity__gt=0).distinct(),
            "active": "documents_dw",
            "today": date.today().isoformat(),
            "items": [],
            "selected_employee": employee_id,
        }
        return render(request, "documents/create_dw.html", context)

    def post(self, request):
        employee_id = request.POST.get("employee")
        issue_date = parse_date_or_none(request.POST.get("issue_date"))

        product_ids = request.POST.getlist("product_id[]")
        quantities = request.POST.getlist("quantity[]")
        sizes = request.POST.getlist("size[]")
        unit_prices = request.POST.getlist("unit_price[]")
        notes = request.POST.getlist("notes[]")

        items_parsed = list(zip(product_ids, quantities, sizes, unit_prices, notes))

        errors = {}
        item_errors = []

        if not employee_id:
            errors["employee"] = "Wybierz pracownika"
        if not issue_date:
            errors["issue_date"] = "Podaj datę wystawienia"

        for i, (pid, qty_raw, size, unit_price, note) in enumerate(items_parsed):
            line_number = i + 1
            pid = pid.strip()
            qty_raw = qty_raw.strip()

            if not pid and not qty_raw:
                continue

            if not pid:
                item_errors.append(f"W pozycji {line_number}: nie wybrano produktu.")
                continue

            try:
                qty = int(qty_raw)
                if qty <= 0:
                    raise ValueError
            except Exception:
                item_errors.append(f"W pozycji {line_number}: niepoprawna ilość („{qty_raw}”).")
                continue

            items_parsed[i] = (pid, qty, size.strip(), unit_price.strip(), note.strip())

        if not any(pid for pid, *_ in items_parsed):
            errors["items"] = "Dodaj przynajmniej jedną poprawną pozycję"

        if item_errors:
            errors["item_errors"] = item_errors

        if errors:
            context = {
                "employees": Employee.objects.all(),
                "products": Product.objects.all(),
                "errors": errors,
                "items": items_parsed,
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
                for pid, qty, size, unit_price, note in items_parsed:
                    if not pid:
                        continue
                    product = Product.objects.get(pk=pid)
                    DocumentItem.objects.create(
                        document=doc,
                        product=product,
                        quantity=qty,
                        size=size or None,
                        notes=note,
                        unit_price=float(unit_price) if unit_price else None,
                    )
        except Exception as e:
            messages.error(request, f"Błąd zapisu: {e}")
            context = {
                "employees": Employee.objects.all(),
                "products": Product.objects.all(),
                "errors": {"general": str(e)},
                "items": items_parsed,
                "active": "documents_dw",
                "today": date.today().isoformat(),
            }
            return render(request, "documents/create_dw.html", context)

        messages.success(request, f"DW utworzone: {doc.document_number}")
        return redirect(reverse("documents:dw_detail", args=[doc.pk]))


class ReceiptCreateView(LoginRequiredMixin, View):
    """Create a PZ (ReceiptDocument) — przyjęcie zewnętrzne"""

    def get(self, request):
        context = {
            "suppliers": Supplier.objects.all(),
            "companies": Company.objects.all(),
            "products": Product.objects.all(),
            "active": "documents_pz",
            "today": date.today().isoformat(),
            "items": [],
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

        items_parsed = list(zip(product_ids, quantities, sizes, unit_prices, notes))

        errors = {}
        item_errors = []

        if not supplier_id:
            errors["supplier"] = "Wybierz dostawcę"
        if not recipient_id:
            errors["recipient"] = "Wybierz odbiorcę"
        if not issue_date:
            errors["issue_date"] = "Podaj datę wystawienia"

        for i, (pid, qty_raw, size, unit_price, note) in enumerate(items_parsed):
            line_number = i + 1
            pid = pid.strip()
            qty_raw = qty_raw.strip()

            if not pid and not qty_raw:
                continue

            if not pid:
                item_errors.append(f"W pozycji {line_number}: nie wybrano produktu.")
                continue

            try:
                qty = int(qty_raw)
                if qty <= 0:
                    raise ValueError
            except Exception:
                item_errors.append(f"W pozycji {line_number}: niepoprawna ilość („{qty_raw}”).")
                continue

            try:
                up = float(unit_price) if unit_price.strip() else 0.0
            except Exception:
                item_errors.append(f"W pozycji {line_number}: niepoprawna cena („{unit_price}”).")
                continue

            items_parsed[i] = (pid, qty, size.strip(), up, note.strip())

        if not any(pid for pid, *_ in items_parsed):
            errors["items"] = "Dodaj przynajmniej jedną poprawną pozycję"

        if item_errors:
            errors["item_errors"] = item_errors

        if errors:
            context = {
                "suppliers": Supplier.objects.all(),
                "companies": Company.objects.all(),
                "products": Product.objects.all(),
                "errors": errors,
                "items": items_parsed,
                "active": "documents_pz",
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
                    if not pid:
                        continue
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
                "items": items_parsed,
                "active": "documents_pz",
                "today": date.today().isoformat(),
            }
            return render(request, "documents/create_pz.html", context)

        messages.success(request, f"PZ utworzone: {doc.document_number}")
        return redirect(reverse("documents:pz_detail", args=[doc.pk]))


# =====================================================
# =============== EDIT VIEWS ==========================
# =====================================================

class DWEditView(LoginRequiredMixin, View):
    """Edit DW document - basic info and items"""

    def get(self, request, pk):
        doc = get_object_or_404(IssueDocument, pk=pk)
        items = doc.items.select_related("product").all()
        context = {
            "doc": doc,
            "items": items,
            "employees": Employee.objects.all(),
            "products": Product.objects.all(),
            "active": "documents_dw",
            "today": date.today().isoformat(),
        }
        return render(request, "documents/edit_dw.html", context)

    def post(self, request, pk):
        doc = get_object_or_404(IssueDocument, pk=pk)
        
        # Basic document info
        employee_id = request.POST.get("employee")
        issue_date = parse_date_or_none(request.POST.get("issue_date"))
        
        # Existing items
        item_ids = request.POST.getlist("item_id[]")
        quantities = request.POST.getlist("quantity[]")
        sizes = request.POST.getlist("size[]")
        notes = request.POST.getlist("notes[]")
        
        # New items
        new_product_ids = request.POST.getlist("new_product_id[]")
        new_quantities = request.POST.getlist("new_quantity[]")
        new_sizes = request.POST.getlist("new_size[]")
        new_notes = request.POST.getlist("new_notes[]")

        errors = {}
        if not employee_id:
            errors["employee"] = "Wybierz pracownika"
        if not issue_date:
            errors["issue_date"] = "Podaj datę wystawienia"

        # Validate existing items
        existing_items_data = []
        for i, item_id in enumerate(item_ids):
            if not item_id:
                continue
            try:
                qty = int(quantities[i])
                existing_items_data.append((int(item_id), qty, sizes[i], notes[i]))
            except (ValueError, IndexError):
                errors[f"quantity_{i}"] = "Niepoprawna ilość"

        # Validate new items
        new_items_data = []
        for i, pid in enumerate(new_product_ids):
            pid = pid.strip()
            if not pid:
                continue
            try:
                qty = int(new_quantities[i])
                size = new_sizes[i] if i < len(new_sizes) else ""
                note = new_notes[i] if i < len(new_notes) else ""
                new_items_data.append((pid, qty, size, note))
            except (ValueError, IndexError):
                errors[f"new_quantity_{i}"] = "Niepoprawna ilość"

        if errors:
            items = doc.items.select_related("product").all()
            context = {
                "doc": doc,
                "items": items,
                "employees": Employee.objects.all(),
                "products": Product.objects.all(),
                "errors": errors,
                "form": request.POST,
                "active": "documents_dw",
                "today": date.today().isoformat(),
            }
            return render(request, "documents/edit_dw.html", context)

        try:
            with transaction.atomic():
                # Update basic document info
                doc.issue_date = issue_date
                doc.employee_id = employee_id
                doc.save()

                # Update existing items
                for item_id, quantity, size, note in existing_items_data:
                    item = DocumentItem.objects.get(id=item_id, document=doc)
                    old_quantity = item.quantity
                    
                    # Update item
                    item.quantity = quantity
                    item.size = size or None
                    item.notes = note
                    item.save()
                    
                    # Update stock if quantity changed
                    if old_quantity != quantity:
                        from warehouse.models import WarehouseStock, StockMovement
                        
                        warehouse_stock, created = WarehouseStock.objects.get_or_create(
                            product=item.product, 
                            size=item.size, 
                            defaults={"quantity": 0}
                        )
                        
                        # Adjust stock based on difference
                        quantity_diff = old_quantity - quantity
                        warehouse_stock.update_stock(quantity_diff)
                        
                        # Record movement
                        StockMovement.objects.create(
                            product=item.product,
                            size=item.size,
                            movement_type="in" if quantity_diff > 0 else "out",
                            quantity=abs(quantity_diff),
                            document_type="DW_CORRECTION",
                            document_id=doc.id,
                            notes=f"Korekta DW: {doc.document_number}",
                        )

                # Add new items
                for pid, qty, size, note in new_items_data:
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
            items = doc.items.select_related("product").all()
            context = {
                "doc": doc,
                "items": items,
                "employees": Employee.objects.all(),
                "products": Product.objects.all(),
                "errors": {"general": str(e)},
                "form": request.POST,
                "active": "documents_dw",
                "today": date.today().isoformat(),
            }
            return render(request, "documents/edit_dw.html", context)

        messages.success(request, f"DW zaktualizowane: {doc.document_number}")
        return redirect(reverse("documents:dw_detail", args=[doc.pk]))


class PZEditView(LoginRequiredMixin,View):
    """Edit PZ document - basic info and items"""

    def get(self, request, pk):
        doc = get_object_or_404(ReceiptDocument, pk=pk)
        items = doc.items.select_related("product").all()
        context = {
            "doc": doc,
            "items": items,
            "suppliers": Supplier.objects.all(),
            "companies": Company.objects.all(),
            "products": Product.objects.all(),
            "active": "documents_pz",
            "today": date.today().isoformat(),
        }
        return render(request, "documents/edit_pz.html", context)

    def post(self, request, pk):
        doc = get_object_or_404(ReceiptDocument, pk=pk)
        
        # Basic document info
        supplier_id = request.POST.get("supplier")
        recipient_id = request.POST.get("recipient")
        issue_date = parse_date_or_none(request.POST.get("issue_date"))
        
        # Existing items
        item_ids = request.POST.getlist("item_id[]")
        quantities = request.POST.getlist("quantity[]")
        sizes = request.POST.getlist("size[]")
        unit_prices = request.POST.getlist("unit_price[]")
        notes = request.POST.getlist("notes[]")
        
        # New items
        new_product_ids = request.POST.getlist("new_product_id[]")
        new_quantities = request.POST.getlist("new_quantity[]")
        new_sizes = request.POST.getlist("new_size[]")
        new_unit_prices = request.POST.getlist("new_unit_price[]")
        new_notes = request.POST.getlist("new_notes[]")

        errors = {}
        if not supplier_id:
            errors["supplier"] = "Wybierz dostawcę"
        if not recipient_id:
            errors["recipient"] = "Wybierz odbiorcę"
        if not issue_date:
            errors["issue_date"] = "Podaj datę wystawienia"

        # Validate existing items
        existing_items_data = []
        for i, item_id in enumerate(item_ids):
            if not item_id:
                continue
            try:
                qty = int(quantities[i])
                up = float(unit_prices[i]) if i < len(unit_prices) and unit_prices[i].strip() else 0.0
                existing_items_data.append((int(item_id), qty, sizes[i], up, notes[i]))
            except (ValueError, IndexError):
                errors[f"quantity_{i}"] = "Niepoprawna ilość lub cena"

        # Validate new items
        new_items_data = []
        for i, pid in enumerate(new_product_ids):
            pid = pid.strip()
            if not pid:
                continue
            try:
                qty = int(new_quantities[i])
                up = float(new_unit_prices[i]) if i < len(new_unit_prices) and new_unit_prices[i].strip() else 0.0
                size = new_sizes[i] if i < len(new_sizes) else ""
                note = new_notes[i] if i < len(new_notes) else ""
                new_items_data.append((pid, qty, size, up, note))
            except (ValueError, IndexError):
                errors[f"new_quantity_{i}"] = "Niepoprawna ilość lub cena"

        if errors:
            items = doc.items.select_related("product").all()
            context = {
                "doc": doc,
                "items": items,
                "suppliers": Supplier.objects.all(),
                "companies": Company.objects.all(),
                "products": Product.objects.all(),
                "errors": errors,
                "form": request.POST,
                "active": "documents_pz",
                "today": date.today().isoformat(),
            }
            return render(request, "documents/edit_pz.html", context)

        try:
            with transaction.atomic():
                # Update basic document info
                doc.issue_date = issue_date
                doc.supplier_id = supplier_id
                doc.recipient_id = recipient_id
                doc.save()

                # Update existing items
                for item_id, quantity, size, unit_price, note in existing_items_data:
                    item = ReceiptItem.objects.get(id=item_id, document=doc)
                    old_quantity = item.quantity
                    
                    # Update item
                    item.quantity = quantity
                    item.size = size or None
                    item.unit_price = unit_price
                    item.total_value = quantity * unit_price
                    item.notes = note
                    item.save()
                    
                    # Update stock if quantity changed
                    if old_quantity != quantity:
                        from warehouse.models import WarehouseStock, StockMovement
                        
                        warehouse_stock, created = WarehouseStock.objects.get_or_create(
                            product=item.product, 
                            size=item.size, 
                            defaults={"quantity": 0}
                        )
                        
                        # Adjust stock based on difference
                        quantity_diff = quantity - old_quantity
                        warehouse_stock.update_stock(quantity_diff)
                        
                        # Record movement
                        StockMovement.objects.create(
                            product=item.product,
                            size=item.size,
                            movement_type="in" if quantity_diff > 0 else "out",
                            quantity=abs(quantity_diff),
                            document_type="PZ_CORRECTION",
                            document_id=doc.id,
                            notes=f"Korekta PZ: {doc.document_number}",
                        )

                # Add new items
                for pid, qty, size, up, note in new_items_data:
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
            items = doc.items.select_related("product").all()
            context = {
                "doc": doc,
                "items": items,
                "suppliers": Supplier.objects.all(),
                "companies": Company.objects.all(),
                "products": Product.objects.all(),
                "errors": {"general": str(e)},
                "form": request.POST,
                "active": "documents_pz",
                "today": date.today().isoformat(),
            }
            return render(request, "documents/edit_pz.html", context)

        messages.success(request, f"PZ zaktualizowane: {doc.document_number}")
        return redirect(reverse("documents:pz_detail", args=[doc.pk]))


# =====================================================
# =============== ITEM VIEWS ==========================
# =====================================================

class ItemMarkUsedView(LoginRequiredMixin,View):
    """Mark a DocumentItem as used (DW only)"""

    def post(self, request, item_id):
        it = get_object_or_404(DocumentItem, pk=item_id)
        it.mark_as_used()
        messages.success(request, "Pozycja oznaczona jako zużyta")
        return redirect(reverse("employees:detail", args=[it.document.employee_id]))


class ItemDeleteView(LoginRequiredMixin,View):
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

class DWListView(LoginRequiredMixin,View):
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
            "documents": qs.order_by("-issue_date").order_by("-document_number"),
            "q": q,
            "company": company_id,
            "companies": Company.objects.all().order_by("name"),
            "active": "documents_dw",
            "doc_type": "DW",
        }
        return render(request, "documents/list_dw.html", context)


class PZListView(LoginRequiredMixin,View):
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
            "documents": qs.order_by("-issue_date").order_by("-document_number"),
            "q": q,
            "supplier": supplier_id,
            "recipient": recipient_id,
            "suppliers": Supplier.objects.all().order_by("name"),
            "recipients": Company.objects.all().order_by("name"),
            "active": "documents_pz",
            "doc_type": "PZ",
        }
        return render(request, "documents/list_pz.html", context)
    

# =====================================================
# =============== PENDING PRODUCTS VIEWS ==============
# =====================================================
class PendingReceiptListView(View):
    def get(self, request):
        docs = PendingReceiptDocument.objects.order_by("-created_at")
        return render(request, "documents/pending_receipt_list.html", {
            "documents": docs
        })


class PendingReceiptDeleteView(View):
    def post(self, request, pk):
        get_object_or_404(PendingReceiptDocument, pk=pk).delete()
        messages.success(request, "Usunięto dokument.")
        return redirect("documents:pending_receipt_list")


class PendingReceiptDetailView(View):
    def get(self, request, pk):
        doc = get_object_or_404(PendingReceiptDocument, pk=pk)
        return render(request, "documents/pending_receipt_detail.html", {
            "doc": doc,
            "suppliers": Supplier.objects.all(),
            "companies": Company.objects.all(),
            "products": Product.objects.all(),
        })

    
    @transaction.atomic
    def post(self, request, pk):
        doc = get_object_or_404(PendingReceiptDocument, pk=pk)

        doc.supplier_id = request.POST.get("supplier") or None
        doc.recipient_id = request.POST.get("recipient") or None

        delivery_raw = request.POST.get("delivery_date")
        try:
            doc.delivery_date = datetime.strptime(delivery_raw, "%Y-%m-%d").date() if delivery_raw else None
        except (ValueError, TypeError):
            doc.delivery_date = None
        doc.save()

        post = request.POST
        incoming_ids = set()

        existing_items = {str(i.id): i for i in doc.items.select_related("product").all()}
        new_pending = []

        for key in post:
            if not key.startswith("product_"):
                continue

            item_id = key.replace("product_", "").strip()
            incoming_ids.add(item_id)

            product_id = post.get(f"product_{item_id}")
            delivered_raw = post.get(f"delivered_{item_id}") or "0"

            try:
                delivered = int(float(delivered_raw))
            except (ValueError, TypeError):
                delivered = 0

            if not product_id:
                continue

            try:
                product = Product.objects.get(pk=product_id)
            except Product.DoesNotExist:
                continue

            if item_id.startswith("new_"):
                print("Creating new pending item")
                new_pending.append(PendingReceiptItem(
                    document=doc,
                    product=product,
                    quantity_delivered=delivered,
                ))
            else:
                item = existing_items.get(item_id)
                if not item:
                    continue
                item.product = product
                item.quantity_delivered = delivered
                item.save()

        if new_pending:
            print("Bulk creating new pending items")
            created_items = PendingReceiptItem.objects.bulk_create(new_pending)
            new_pending_ids = {str(item.id) for item in created_items}
            incoming_ids.update(new_pending_ids)

        db_ids = {str(i.id) for i in doc.items.all()}
        to_delete = db_ids - incoming_ids
        if to_delete:
            PendingReceiptItem.objects.filter(id__in=to_delete).delete()

        if "approve" in post:
            issue_date = doc.delivery_date or date.today()
            new_doc = ReceiptDocument.objects.create(
                supplier=doc.supplier,
                recipient=doc.recipient,
                issue_date=issue_date,
            )

            receipt_items = []
            for item in doc.items.select_related("product").all():
                if not item.product:
                    continue
                unit_price = item.product.unit_price or 0
                qty = item.quantity_delivered or 0
                receipt_items.append(ReceiptItem(
                    document=new_doc,
                    product=item.product,
                    quantity=qty,
                    size=item.product.size or "",
                    unit_price=unit_price,
                    total_value=unit_price * qty,
                    notes=getattr(item, "description", "") or "",
                ))

            if receipt_items:
                ReceiptItem.objects.bulk_create(receipt_items)

            doc.items.all().delete()
            doc.delete()

            messages.success(request, "Dokument został zatwierdzony.")
            return redirect("documents:pending_receipt_list")

        return redirect("documents:pending_receipt_detail", pk=pk)
