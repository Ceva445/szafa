from django.db import models
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

class EmploymentPeriod(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='employment_periods')
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.employee} - {self.start_date} to {self.end_date or 'present'}"