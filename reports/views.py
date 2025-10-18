from django.views import View
from django.shortcuts import render
from django.db.models import Q, Sum
from datetime import datetime, date, timedelta
from employees.models import Employee, EmploymentPeriod
from documents.models import IssueDocument, DocumentItem, ReceiptDocument, ReceiptItem
from core.models import Company, Department, Supplier
from warehouse.models import WarehouseStock
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
        else:
            # Якщо звіт не вибрано, показуємо інструкцію
            return render(request, "reports/reports_base.html", context)

    def render_order_demand_report(self, request, context):
        """Рендеринг звіту запотребowania на замówienie на основі видань."""
        months_ahead = int(request.GET.get("months_ahead", 1))
        show_zero_demand = request.GET.get("show_zero_demand", "false") == "true"
        output_format = request.GET.get("output", "screen")

        today = date.today()
        start_date = today
        end_date = today + timedelta(days=30 * months_ahead)

        # --- Прогноз майбутніх видань ---
        future_issues = (
            DocumentItem.objects.filter(
                next_issue_date__range=[start_date, end_date], status="active"
            )
            .values(
                "product__id",
                "product__code",
                "product__name",
                "product__min_qty_on_stock",
                "size",
            )
            .annotate(total_needed=Sum("quantity"))
            .order_by("product__code", "size")
        )

        # --- Поточні запаси ---
        stock_data = {}
        for stock in WarehouseStock.objects.all():
            key = f"{stock.product_id}_{stock.size}"
            stock_data[key] = stock.quantity

        # --- Формування даних ---
        order_demand_data = []
        total_order_need = 0

        for issue in future_issues:
            product_id = issue["product__id"]
            size = issue["size"] or ""
            key = f"{product_id}_{size}"

            current_stock = stock_data.get(key, 0)
            min_stock = issue["product__min_qty_on_stock"] or 0
            total_needed = issue["total_needed"] or 0

            order_need = (total_needed + min_stock) - current_stock
            order_need = max(0, order_need)

            if order_need > 0 or show_zero_demand:
                order_demand_data.append(
                    {
                        "product_code": issue["product__code"],
                        "product_name": issue["product__name"],
                        "size": size,
                        "current_stock": current_stock,
                        "min_stock": min_stock,
                        "forecast_issues": total_needed,
                        "order_need": order_need,
                        "period": f"{start_date} - {end_date}",
                    }
                )
                total_order_need += order_need

        # --- Оновлюємо контекст ---
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

        # --- Формати експорту ---
        if output_format == "xls":
            data = [
                [
                    item["product_name"],
                    item["size"] or "-",
                    item["forecast_issues"],
                    item["min_stock"],
                    item["current_stock"],
                    item["order_need"],
                ]
                for item in order_demand_data
            ]
            columns = [
                "Produkt",
                "Rozmiar",
                "Prognoza wydań",
                "Min. stan",
                "Stan magazynowy",
                "Do zamówienia",
            ]
            return export_to_excel(
                data, columns, filename="zapotrzebowanie_na_zamówienie.xlsx"
            )

        elif output_format == "pdf":
            data = [
                [
                    item["product_name"],
                    item["size"] or "-",
                    str(item["forecast_issues"]),
                    str(item["min_stock"]),
                    str(item["current_stock"]),
                    str(item["order_need"]),
                ]
                for item in order_demand_data
            ]
            columns = [
                "Produkt",
                "Rozmiar",
                "Prognoza wydań",
                "Min. stan",
                "Stan magazynowy",
                "Do zamówienia",
            ]
            return export_to_pdf(
                data,
                columns,
                title="Zapotrzebowanie na zamówienie",
                filename="zapotrzebowanie_na_zamówienie.pdf",
            )

        # --- Екранний режим ---
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

        if output_format == "xls":
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
            return export_to_excel(
                data, columns, filename="raport_zapotrzebowania.xlsx"
            )

        elif output_format == "pdf":
            data = [
                [
                    str(item.document.employee.id),
                    item.document.employee.last_name,
                    item.document.employee.first_name,
                    item.product.name,
                    item.size or "-",
                    (
                        item.next_issue_date.strftime("%Y-%m-%d")
                        if item.next_issue_date
                        else ""
                    ),
                    str(item.quantity),
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

        if output_format == "xls":
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
            return export_to_excel(data, columns, filename="raport_wydan.xlsx")

        elif output_format == "pdf":
            data = [
                [
                    str(item.document.employee.id),
                    item.document.employee.last_name,
                    item.document.employee.first_name,
                    item.product.name,
                    item.size or "-",
                    (
                        item.document.issue_date.strftime("%Y-%m-%d")
                        if item.document.issue_date
                        else ""
                    ),
                    str(item.quantity),
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

        if output_format == "xls":
            data = [
                [
                    item.document.supplier.name if item.document.supplier else "-",
                    item.product.name,
                    item.size or "-",
                    (
                        item.document.receipt_date.strftime("%Y-%m-%d")
                        if item.document.receipt_date
                        else ""
                    ),
                    item.quantity,
                ]
                for item in document_items
            ]
            columns = ["Dostawca", "Produkt", "Rozmiar", "Data przyjęcia", "Ilość"]
            return export_to_excel(data, columns, filename="raport_przyjec.xlsx")

        elif output_format == "pdf":
            data = [
                [
                    item.document.supplier.name if item.document.supplier else "-",
                    item.product.name,
                    item.size or "-",
                    (
                        item.document.receipt_date.strftime("%Y-%m-%d")
                        if item.document.receipt_date
                        else ""
                    ),
                    str(item.quantity),
                ]
                for item in document_items
            ]
            columns = ["Dostawca", "Produkt", "Rozmiar", "Data przyjęcia", "Ilość"]
            return export_to_pdf(
                data, columns, title="Raport przyjęć", filename="raport_przyjec.pdf"
            )

        return render(request, "reports/reports_base.html", context)
