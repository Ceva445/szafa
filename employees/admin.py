from django.contrib import admin
from django import forms
from .models import Employee, EmploymentPeriod


class EmploymentPeriodForm(forms.ModelForm):
    class Meta:
        model = EmploymentPeriod
        fields = ["start_date", "end_date"]

    def clean(self):
        cleaned_data = super().clean()
        # Додаткова валідація, якщо потрібно
        return cleaned_data


class EmploymentPeriodInline(admin.TabularInline):
    model = EmploymentPeriod
    form = EmploymentPeriodForm
    extra = 1
    fields = ["start_date", "end_date"]

    def get_formset(self, request, obj=None, **kwargs):
        # Відкласти валідацію періодів роботи до збереження працівника
        formset = super().get_formset(request, obj, **kwargs)
        formset.validate_min = False
        formset.validate_max = False
        return formset


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

    def save_formset(self, request, form, formset, change):
        # Спочатку зберегти працівника
        instances = formset.save(commit=False)
        for instance in instances:
            # Переконатися, що працівник встановлений
            if not instance.employee_id:
                instance.employee = form.instance
            instance.save()
        formset.save_m2m()


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
