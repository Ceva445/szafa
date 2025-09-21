from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from datetime import date
from django.db import transaction
from django.core.exceptions import ValidationError


@receiver(post_save, sender="employees.EmploymentPeriod")
def handle_employment_period_change(sender, instance, **kwargs):
    """Processing changes in work periods"""
    if instance.end_date and instance.end_date <= date.today():
        deactivate_employee_products(instance.employee)


def deactivate_employee_products(employee):
    """Deactivate employee products upon termination"""
    from documents.models import DocumentItem

    active_items = DocumentItem.objects.filter(
        document__employee=employee, status="active"
    )

    for item in active_items:
        item.status = "used"
        item.auto_deactivated = True

    if active_items:
        DocumentItem.objects.bulk_update(active_items, ["status", "auto_deactivated"])


@receiver(post_save, sender="employees.Employee")
def validate_employment_periods(sender, instance, created, **kwargs):
    """Validate employment periods after employee is saved"""
    if created and instance.employment_periods.exists():
        for period in instance.employment_periods.all():
            try:
                period.full_clean()
            except ValidationError as e:
                print(f"Validation error for period {period}: {e}")


@receiver(pre_save, sender="employees.EmploymentPeriod")
def validate_employment_period_before_save(sender, instance, **kwargs):
    """Pre-save validation of employment period"""
    try:
        instance.full_clean()
    except ValidationError as e:
        print(f"Pre-save validation error: {e}")
