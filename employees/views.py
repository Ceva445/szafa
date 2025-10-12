from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.urls import reverse
from django.db import IntegrityError, transaction
from django.contrib import messages
from datetime import datetime
from .models import Employee, EmploymentPeriod
from core.models import Company, Position, Department
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError

from django.db.models import Q

DATE_FMT = "%Y-%m-%d"


def parse_date_or_none(val):
    val = (val or "").strip()
    if not val:
        return None
    try:
        return datetime.strptime(val, DATE_FMT).date()
    except ValueError:
        return None


class EmployeesListView(LoginRequiredMixin, View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        company_id = request.GET.get("company")
        position_id = request.GET.get("position")

        qs = Employee.objects.all().select_related("position", "company", "department")

        if company_id:
            qs = qs.filter(company_id=company_id)
        if position_id:
            qs = qs.filter(position_id=position_id)
        if q:
            qs = qs.filter(
                Q(card_number__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
            )

        context = {
            "employees": qs,
            "companies": Company.objects.all(),
            "positions": Position.objects.all(),
            "departments": Department.objects.all(),
            "active": "employees",
        }
        return render(request, "employees/list.html", context)

    def post(self, request):
        # POST left intentionally empty per spec
        pass


class AddEmployeeView(LoginRequiredMixin, View):
    def get(self, request):
        context = {
            "companies": Company.objects.all(),
            "positions": Position.objects.all(),
            "departments": Department.objects.all(),
            "active": "employees",
            "form": {},  # empty for template
            "errors": {},
        }
        return render(request, "employees/add.html", context)

    def post(self, request):
        # Collect fields manually (no Django forms)
        card_number = request.POST.get("card_number", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        position_id = request.POST.get("position")
        department_id = request.POST.get("department")
        company_id = request.POST.get("company")

        # Employment periods arrays
        start_dates = request.POST.getlist("start_date[]")
        end_dates = request.POST.getlist("end_date[]")

        errors = {}
        if not card_number:
            errors["card_number"] = "NR Karty wymagany"
        if not first_name:
            errors["first_name"] = "Imię wymagane"
        if not last_name:
            errors["last_name"] = "Nazwisko wymagane"
        if not position_id:
            errors["position"] = "Wybierz stanowisko"
        if not department_id:
            errors["department"] = "Wybierz dział"
        if not company_id:
            errors["company"] = "Wybierz firmę"

        # parse employment periods
        periods = []
        for i, sd in enumerate(start_dates):
            sd_parsed = parse_date_or_none(sd)
            ed_parsed = parse_date_or_none(end_dates[i]) if i < len(end_dates) else None
            if not sd_parsed:
                # if both empty skip row
                if not sd and (not end_dates or not end_dates[i].strip()):
                    continue
                errors[f"period_{i}"] = "Niepoprawna data rozpoczęcia"
            else:
                periods.append((sd_parsed, ed_parsed))

        if errors:
            context = {
                "companies": Company.objects.all(),
                "positions": Position.objects.all(),
                "departments": Department.objects.all(),
                "active": "employees",
                "form": request.POST,
                "errors": errors,
            }
            return render(request, "employees/add.html", context)

        try:
            with transaction.atomic():
                emp = Employee.objects.create(
                    card_number=card_number,
                    first_name=first_name,
                    last_name=last_name,
                    position_id=position_id,
                    department_id=department_id,
                    company_id=company_id,
                )
                for sd, ed in periods:
                    EmploymentPeriod.objects.create(
                        employee=emp, start_date=sd, end_date=ed
                    )
        except IntegrityError as e:
            errors["card_number"] = "NR Karty musi być unikalny"
            context = {
                "companies": Company.objects.all(),
                "positions": Position.objects.all(),
                "departments": Department.objects.all(),
                "active": "employees",
                "form": request.POST,
                "errors": errors,
            }
            return render(request, "employees/add.html", context)

        messages.success(request, "Pracownik dodany")
        return redirect(reverse("employees:list"))


class EditEmployeeView(LoginRequiredMixin, View):
    def get(self, request, pk):
        emp = get_object_or_404(Employee, pk=pk)
        # prepare form initial
        initial = {
            "card_number": emp.card_number,
            "first_name": emp.first_name,
            "last_name": emp.last_name,
            "position": emp.position_id,
            "department": emp.department_id,
            "company": emp.company_id,
        }
        periods = list(emp.employment_periods.all().order_by("start_date"))
        context = {
            "employee": emp,
            "companies": Company.objects.all(),
            "positions": Position.objects.all(),
            "departments": Department.objects.all(),
            "initial": initial,
            "periods": periods,
            "active": "employees",
            "errors": {},
        }
        return render(request, "employees/edit.html", context)

    def post(self, request, pk):
        emp = get_object_or_404(Employee, pk=pk)
        card_number = request.POST.get("card_number", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        position_id = request.POST.get("position")
        department_id = request.POST.get("department")
        company_id = request.POST.get("company")

        start_dates = request.POST.getlist("start_date[]")
        end_dates = request.POST.getlist("end_date[]")

        errors = {}
        if not card_number:
            errors["card_number"] = "NR Karty wymagany"
        if not first_name:
            errors["first_name"] = "Imię wymagane"
        if not last_name:
            errors["last_name"] = "Nazwisko wymagane"
        if not position_id:
            errors["position"] = "Wybierz stanowisko"
        if not department_id:
            errors["department"] = "Wybierz dział"
        if not company_id:
            errors["company"] = "Wybierz firmę"

        periods = []
        for i, sd in enumerate(start_dates):
            sd_parsed = parse_date_or_none(sd)
            ed_parsed = parse_date_or_none(end_dates[i]) if i < len(end_dates) else None
            if not sd_parsed:
                if not sd and (not end_dates or not end_dates[i].strip()):
                    continue
                errors[f"period_{i}"] = "Niepoprawna data rozpoczęcia"
            else:
                periods.append((sd_parsed, ed_parsed))

        if errors:
            context = {
                "employee": emp,
                "companies": Company.objects.all(),
                "positions": Position.objects.all(),
                "departments": Department.objects.all(),
                "initial": request.POST,
                "periods": periods,
                "active": "employees",
                "errors": errors,
            }
            return render(request, "employees/edit.html", context)

        # save changes
        try:
            with transaction.atomic():
                emp.card_number = card_number
                emp.first_name = first_name
                emp.last_name = last_name
                emp.position_id = position_id
                emp.department_id = department_id
                emp.company_id = company_id
                emp.save()

                # clear and recreate periods (EmploymentPeriod.clean will validate overlaps)
                emp.employment_periods.all().delete()
                for sd, ed in periods:
                    EmploymentPeriod.objects.create(
                        employee=emp, start_date=sd, end_date=ed
                    )
        except IntegrityError:
            errors["card_number"] = "NR Karty musi być unikalny"
            context = {
                "employee": emp,
                "companies": Company.objects.all(),
                "positions": Position.objects.all(),
                "departments": Department.objects.all(),
                "initial": request.POST,
                "periods": periods,
                "active": "employees",
                "errors": errors,
            }
            return render(request, "employees/edit.html", context)
        except Exception as e:
            # Could be ValidationError from EmploymentPeriod.clean
            errors["general"] = str(e)
            context = {
                "employee": emp,
                "companies": Company.objects.all(),
                "positions": Position.objects.all(),
                "departments": Department.objects.all(),
                "initial": request.POST,
                "periods": periods,
                "active": "employees",
                "errors": errors,
            }
            return render(request, "employees/edit.html", context)

        messages.success(request, "Dane pracownika zaktualizowane")
        return redirect(reverse("employees:detail", args=[emp.pk]))


class DeleteEmployeeView(LoginRequiredMixin, View):
    def post(self, request, pk):
        emp = get_object_or_404(Employee, pk=pk)
        try:
            emp.delete()
            messages.success(request, f"Pracownik {emp.first_name} {emp.last_name} został pomyślnie usunięty.")
        except ProtectedError:
            messages.error(
                request,
                f"Nie można usunąć pracownika {emp.first_name} {emp.last_name}, "
                f"ponieważ ma powiązane dokumenty wydania (DW). "
                f"Najpierw usuń lub zmodyfikuj te dokumenty."
            )
        return redirect(reverse("employees:list"))

class EmployeeDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        emp = get_object_or_404(Employee, pk=pk)
        # get "on stock" and "used" via model helper methods (you have these)
        active_products = emp.get_active_products()  # queryset of DocumentItem
        used_products = emp.get_used_products()
        context = {
            "employee": emp,
            "active_products": active_products,
            "used_products": used_products,
            "active": "employees",
        }
        return render(request, "employees/detail.html", context)
