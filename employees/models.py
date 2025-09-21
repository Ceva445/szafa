from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q
from datetime import date
from core.models import Company, Department, Position


class Employee(models.Model):
    card_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    position = models.ForeignKey(Position, on_delete=models.PROTECT)
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.card_number})"

    def get_current_employment_period(self):
        """Returns the current period of employment of an employee"""
        today = date.today()
        return (
            self.employment_periods.filter(
                Q(end_date__isnull=True) | Q(end_date__gte=today), start_date__lte=today
            )
            .order_by("-start_date")
            .first()
        )

    def get_active_products(self):
        """Returns active products of the employee"""
        from documents.models import DocumentItem

        return DocumentItem.objects.filter(document__employee=self, status="active")

    def get_used_products(self):
        """Returns used products of the employee"""
        from documents.models import DocumentItem

        return DocumentItem.objects.filter(document__employee=self, status="used")

    @property
    def current_end_date(self):
        """Returns the end date of the current period of employment"""
        period = self.get_current_employment_period()
        return period.end_date if period else None

    class Meta:
        ordering = ["last_name", "first_name"]


class EmploymentPeriod(models.Model):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="employment_periods"
    )
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Employment Period"
        verbose_name_plural = "Employment Periods"

    def __str__(self):
        return f"{self.employee} - {self.start_date} to {self.end_date or 'present'}"

    def clean(self):
        """Validating employment period dates"""
        if self.end_date and self.end_date <= self.start_date:
            raise ValidationError(
                {"end_date": "End date must be later than start date"}
            )

        # Only check for overlapping periods if employee is saved
        if self.employee and self.employee.pk:
            overlapping_periods = (
                EmploymentPeriod.objects.filter(employee=self.employee)
                .exclude(pk=self.pk if self.pk else None)
                .filter(Q(end_date__isnull=True) | Q(end_date__gte=self.start_date))
            )

            if self.end_date:
                overlapping_periods = overlapping_periods.filter(
                    start_date__lte=self.end_date
                )

            if overlapping_periods.exists():
                raise ValidationError("Employment periods cannot overlap")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

        # Update employee status only if employee exists
        if self.employee and self.employee.pk:
            self.update_employee_status()

            # If the period has ended, move products
            if self.end_date and self.end_date <= date.today():
                from employees.signals import deactivate_employee_products

                deactivate_employee_products(self.employee)

    def update_employee_status(self):
        """Updates the active status of the employee based on periods"""
        today = date.today()
        has_active_period = self.employee.employment_periods.filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today), start_date__lte=today
        ).exists()

        if self.employee.is_active != has_active_period:
            self.employee.is_active = has_active_period
            self.employee.save(update_fields=["is_active"])
