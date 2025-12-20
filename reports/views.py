from urllib import request
from django.views import View
from django.shortcuts import render
from django.db.models import Q, Sum, F
from datetime import datetime, date, timedelta
from employees.models import Employee, EmploymentPeriod
from documents.models import IssueDocument, DocumentItem, ReceiptDocument, ReceiptItem
from core.models import Company, Department, Supplier, Product
from warehouse.models import StockMovement, WarehouseStock
from .utils import export_to_excel, export_to_pdf


class ReportsView(View):
    """Головна сторінка звітів з вибором типу звіту"""

    def get(self, request):
        report_type = request.GET.get("report_type", "")

        context = {
            "active": "reports",
            "report_type": report_type,
            "companies": Company.objects.all(),
            "departments": Department.objects.all(),
            "suppliers": Supplier.objects.all(),
        }

        # Відображення відповідного звіту в залежності від вибору
        if report_type == "demand":
            return self.render_demand_report(request, context)
        elif report_type == "issues":
            return self.render_issues_report(request, context)
        elif report_type == "receipts":
            return self.render_receipts_report(request, context)
        elif report_type == "order_demand":
            return self.render_order_demand_report(request, context)
        elif report_type == "stock_correction":
            return self.render_stock_correction_report(request, context)
        else:
            # Якщо звіт не вибрано, показуємо інструкцію
            return render(request, "reports/reports_base.html", context)

    def render_order_demand_report(self, request, context):
        months_ahead = int(request.GET.get("months_ahead", 1))
        show_zero_demand = request.GET.get("show_zero_demand", "false") == "true"
        output_format = request.GET.get("output", "screen")

        today = date.today()
        start_date = today
        end_date = today + timedelta(days=30 * months_ahead)

        # --- Прогноз майбутніх видань ---
        future_issues = (
            DocumentItem.objects.filter(
                Q(next_issue_date__range=[start_date, end_date]), status="active"
            )
            .values("product_id")
            .annotate(total_needed=Sum("quantity"))
        )

        future_issue_map = {i["product_id"]: i["total_needed"] for i in future_issues}

        # --- Дані про склад ---
        stock_map = {s.product_id: s.quantity for s in WarehouseStock.objects.all()}

        # --- Головний queryset продуктів ---
        products_qs = Product.objects.all()

        # Якщо показуємо лише продукти, які мають потребу або низький запас
        if not show_zero_demand:
            products_qs = products_qs.filter(
                Q(id__in=future_issue_map.keys())
                | Q(
                    id__in=[
                        pid
                        for pid, qty in stock_map.items()
                        if qty < Product.objects.get(id=pid).min_qty_on_stock
                    ]
                )
            )

        order_demand_data = []

        for product in products_qs.only(
            "id", "code", "name", "min_qty_on_stock", "unit_price"
        ):
            product_id = product.id
            current_stock = stock_map.get(product_id, 0)
            min_stock = product.min_qty_on_stock or 0
            forecast_issues = future_issue_map.get(product_id, 0)

            order_need = max(0, (forecast_issues + min_stock) - current_stock)

            # Якщо не показуємо нульову потребу — пропускаємо
            if not show_zero_demand and order_need == 0:
                continue

            order_demand_data.append(
                {
                    "product_code": product.code,
                    "product_name": product.name,
                    "size": "-",
                    "current_stock": current_stock,
                    "min_stock": min_stock,
                    "forecast_issues": forecast_issues,
                    "order_need": order_need,
                    "period": f"{start_date} - {end_date}",
                }
            )

        total_order_need = sum(i["order_need"] for i in order_demand_data)

        context.update(
            {
                "order_demand_data": order_demand_data,
                "total_order_need": total_order_need,
                "filters": {
                    "months_ahead": months_ahead,
                    "show_zero_demand": show_zero_demand,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            }
        )

        # --- Експорт ---
        data = [
            [
                item["product_code"],
                item["order_need"],
                item["product_name"],
                item["size"],
                item["forecast_issues"],
                item["min_stock"],
                item["current_stock"],
            ]
            for item in order_demand_data
        ]

        columns = [
            "Kod produktu",
            "Do zamówienia",
            "Produkt",
            "Rozmiar",
            "Prognoza wydań",
            "Min. stan",
            "Stan magazynowy",
        ]
        if output_format == "xls":
            return export_to_excel(
                data, columns, filename="zapotrzebowanie_na_zamówienie.xlsx"
            )

        elif output_format == "pdf":
            return export_to_pdf(
                data,
                columns,
                title="Zapotrzebowanie na zamówienie",
                filename="zapotrzebowanie_na_zamówienie.pdf",
            )

        return render(request, "reports/reports_base.html", context)

    def render_demand_report(self, request, context):
        """Рендеринг звіту потреб"""
        # Отримуємо параметри фільтрів
        company_id = request.GET.get("company", "")
        department_id = request.GET.get("department", "")
        date_from = request.GET.get("date_from", "")
        date_to = request.GET.get("date_to", "")
        sort_by = request.GET.get("sort_by", "employee_end_date")
        output_format = request.GET.get("output", "screen")

        # Базовий запит для активних продуктів працівників
        document_items = DocumentItem.objects.filter(
            status="active", next_issue_date__isnull=False
        ).select_related("document__employee", "product")

        # Застосовуємо фільтри
        if company_id:
            document_items = document_items.filter(
                document__employee__company_id=company_id
            )

        if department_id:
            document_items = document_items.filter(
                document__employee__department_id=department_id
            )

        if date_from:
            document_items = document_items.filter(next_issue_date__gte=date_from)

        if date_to:
            document_items = document_items.filter(next_issue_date__lte=date_to)

        # Сортування
        if sort_by == "employee_end_date":
            document_items = document_items.order_by(
                "document__employee__id", "next_issue_date"
            )
        elif sort_by == "end_date_employee":
            document_items = document_items.order_by(
                "next_issue_date", "document__employee__id"
            )

        context.update(
            {
                "document_items": document_items,
                "filters": {
                    "company": company_id,
                    "department": department_id,
                    "date_from": date_from,
                    "date_to": date_to,
                    "sort_by": sort_by,
                    "output": output_format,
                },
            }
        )
        data = [
            [
                item.document.employee.id,
                item.document.employee.last_name,
                item.document.employee.first_name,
                item.product.name,
                item.size or "-",
                (
                    item.next_issue_date.strftime("%Y-%m-%d")
                    if item.next_issue_date
                    else ""
                ),
                item.quantity,
            ]
            for item in document_items
        ]
        columns = [
            "ID pracownika",
            "Nazwisko",
            "Imię",
            "Produkt",
            "Rozmiar",
            "Data zakończenia",
            "Ilość",
        ]
        if output_format == "xls":
            return export_to_excel(
                data, columns, filename="raport_zapotrzebowania.xlsx"
            )

        elif output_format == "pdf":
            return export_to_pdf(
                data,
                columns,
                title="Raport zapotrzebowania",
                filename="raport_zapotrzebowania.pdf",
            )

        return render(request, "reports/reports_base.html", context)

    def render_issues_report(self, request, context):
        """Рендеринг звіту видань"""
        company_id = request.GET.get("company", "")
        department_id = request.GET.get("department", "")
        date_from = request.GET.get("date_from", "")
        date_to = request.GET.get("date_to", "")
        sort_by = request.GET.get("sort_by", "employee_end_date")
        output_format = request.GET.get("output", "screen")

        # Базовий запит для документів видань
        document_items = DocumentItem.objects.select_related(
            "document__employee", "product"
        )

        # Фільтр по даті видачі
        if date_from:
            document_items = document_items.filter(document__issue_date__gte=date_from)

        if date_to:
            document_items = document_items.filter(document__issue_date__lte=date_to)

        # Додаткові фільтри
        if company_id:
            document_items = document_items.filter(
                document__employee__company_id=company_id
            )

        if department_id:
            document_items = document_items.filter(
                document__employee__department_id=department_id
            )

        # Сортування
        if sort_by == "employee_end_date":
            document_items = document_items.order_by(
                "document__employee__id", "document__issue_date"
            )
        elif sort_by == "end_date_employee":
            document_items = document_items.order_by(
                "document__issue_date", "document__employee__id"
            )

        context.update(
            {
                "document_items": document_items,
                "filters": {
                    "company": company_id,
                    "department": department_id,
                    "date_from": date_from,
                    "date_to": date_to,
                    "sort_by": sort_by,
                    "output": output_format,
                },
            }
        )
        data = [
            [
                item.document.employee.id,
                item.document.employee.last_name,
                item.document.employee.first_name,
                item.product.name,
                item.size or "-",
                (
                    item.document.issue_date.strftime("%Y-%m-%d")
                    if item.document.issue_date
                    else ""
                ),
                item.quantity,
            ]
            for item in document_items
        ]
        columns = [
            "ID pracownika",
            "Nazwisko",
            "Imię",
            "Produkt",
            "Rozmiar",
            "Data wydania",
            "Ilość",
        ]
        if output_format == "xls":
            return export_to_excel(data, columns, filename="raport_wydan.xlsx")

        elif output_format == "pdf":
            return export_to_pdf(
                data, columns, title="Raport wydań", filename="raport_wydan.pdf"
            )

        return render(request, "reports/reports_base.html", context)

    def render_receipts_report(self, request, context):
        """Рендеринг звіту надходжень"""
        supplier_id = request.GET.get("supplier", "")
        recipient_id = request.GET.get("recipient", "")
        date_from = request.GET.get("date_from", "")
        date_to = request.GET.get("date_to", "")
        output_format = request.GET.get("output", "screen")

        # Базовий запит для документів надходження
        receipt_items = ReceiptItem.objects.select_related(
            "document__supplier", "document__recipient", "product"
        )

        # Фільтр по даті
        if date_from:
            receipt_items = receipt_items.filter(document__issue_date__gte=date_from)

        if date_to:
            receipt_items = receipt_items.filter(document__issue_date__lte=date_to)

        # Фільтр по постачальнику
        if supplier_id:
            receipt_items = receipt_items.filter(document__supplier_id=supplier_id)

        # Фільтр по отримувачу
        if recipient_id:
            receipt_items = receipt_items.filter(document__recipient_id=recipient_id)

        context.update(
            {
                "receipt_items": receipt_items,
                "filters": {
                    "supplier": supplier_id,
                    "recipient": recipient_id,
                    "date_from": date_from,
                    "date_to": date_to,
                    "output": output_format,
                },
            }
        )

        data = [
            [
                item.document.supplier.name if item.document.supplier else "-",
                item.document.recipient.name if item.document.recipient else "-",
                item.product.code or "-",
                item.product.name,
                item.size or "-",
                str(item.quantity),
                str(item.unit_price) if item.unit_price is not None else "-",
                str(item.total_value) if item.total_value is not None else "-",
                (
                    item.document.issue_date.strftime("%Y-%m-%d")
                    if item.document.issue_date
                    else ""
                ),
                item.document.document_number or "-",
            ]
            for item in receipt_items
        ]

        columns = [
            "Dostawca",
            "Odbiorca",
            "Kod produktu",
            "Nazwa produktu",
            "Rozmiar",
            "Ilość",
            "Cena",
            "Wartość",
            "Data przyjęcia",
            "Nr dokumentu",
        ]

        if output_format == "xls":
            return export_to_excel(data, columns, filename="raport_przyjec.xlsx")

        elif output_format == "pdf":
            return export_to_pdf(
                data, columns, title="Raport przyjęć", filename="raport_przyjec.pdf"
            )

        return render(request, "reports/reports_base.html", context)

    def render_stock_correction_report(self, request, context):
        """Рендеринг звіту korekty stanu magazynowego"""
        date_from = request.GET.get("date_from", "")
        date_to = request.GET.get("date_to", "")
        product_id = request.GET.get("product", "")
        output_format = request.GET.get("output", "screen")

        # Фільтруємо StockMovement по типу 'stock_correction'
        stock_movements = StockMovement.objects.filter(
            movement_type="stock_correction"
        ).select_related("product")

        if date_from:
            stock_movements = stock_movements.filter(movement_date__gte=date_from)
        if date_to:
            stock_movements = stock_movements.filter(movement_date__lte=date_to)
        if product_id:
            stock_movements = stock_movements.filter(product_id=product_id)

        context.update({
            "stock_movements": stock_movements,
            "filters": {
                "date_from": date_from,
                "date_to": date_to,
                "product": product_id,
                "output": output_format,
            },
        })

        # Підготовка даних для експорту
        data = [
            [
                item.product.code if item.product else "-",
                item.product.name if item.product else "-",
                item.size or "-",
                item.quantity,
                item.notes or "-",
                item.movement_date.strftime("%Y-%m-%d %H:%M"),
                item.document_number or "-",
            ]
            for item in stock_movements
        ]

        columns = [
            "Kod produktu",
            "Nazwa produktu",
            "Rozmiar",
            "Ilość",
            "Uwagi",
            "Data korekty",
            "Nr dokumentu",
        ]

        if output_format == "xls":
            return export_to_excel(data, columns, filename="raport_korekta_stanu.xlsx")
        elif output_format == "pdf":
            return export_to_pdf(
                data,
                columns,
                title="Raport korekty stanu magazynowego",
                filename="raport_korekta_stanu.pdf",
            )

        return render(request, "reports/reports_base.html", context)
