from django.contrib import admin
from .models import Employee, EmploymentPeriod


class EmploymentPeriodInline(admin.TabularInline):
    model = EmploymentPeriod
    extra = 1
    fields = ["start_date", "end_date"]


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        "card_number",
        "first_name",
        "last_name",
        "position",
        "department",
        "company",
        "is_active",
    ]
    list_filter = ["position", "department", "company", "is_active"]
    search_fields = ["card_number", "first_name", "last_name"]
    list_editable = ["is_active"]
    inlines = [EmploymentPeriodInline]


@admin.register(EmploymentPeriod)
class EmploymentPeriodAdmin(admin.ModelAdmin):
    list_display = ["employee", "start_date", "end_date"]
    list_filter = ["start_date", "end_date"]
    search_fields = [
        "employee__first_name",
        "employee__last_name",
        "employee__card_number",
    ]
    date_hierarchy = "start_date"
