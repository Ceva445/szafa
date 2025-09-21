from django.db import models
from core.models import Product, Supplier, Company
from employees.models import Employee

class DocumentBase(models.Model):
    DOCUMENT_TYPES = [
        ('DW', 'Dokument Wydania'),
        ('PZ', 'Przyjęcie Zewnętrzne'),
    ]
    
    document_type = models.CharField(max_length=2, choices=DOCUMENT_TYPES)
    document_number = models.CharField(max_length=50, unique=True)
    issue_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        abstract = True

class IssueDocument(DocumentBase):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT)
    
    def save(self, *args, **kwargs):
        if not self.document_number:
            year = self.issue_date.year
            month = self.issue_date.month
            last_doc = IssueDocument.objects.filter(
                issue_date__year=year,
                issue_date__month=month
            ).order_by('-id').first()
            
            index = 1
            if last_doc:
                index = int(last_doc.document_number.split('/')[-1]) + 1
            
            self.document_number = f"DW/{year}/{month:02d}/{index:04d}"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.document_number

class ReceiptDocument(DocumentBase):
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    recipient = models.ForeignKey(Company, on_delete=models.PROTECT)
    
    def save(self, *args, **kwargs):
        if not self.document_number:
            year = self.issue_date.year
            month = self.issue_date.month
            last_doc = ReceiptDocument.objects.filter(
                issue_date__year=year,
                issue_date__month=month
            ).order_by('-id').first()
            
            index = 1
            if last_doc:
                index = int(last_doc.document_number.split('/')[-1]) + 1
            
            self.document_number = f"PZ/{year}/{month:02d}/{index:04d}"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.document_number

class DocumentItem(models.Model):
    ITEM_STATUS = [
        ('active', 'Aktywny'),
        ('used', 'Zużyty'),
        ('returned', 'Zwrócony'),
    ]
    
    document = models.ForeignKey(IssueDocument, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    size = models.CharField(max_length=20, blank=True, null=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=ITEM_STATUS, default='active')
    next_issue_date = models.DateField(blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if not self.next_issue_date and self.document.issue_date:
            from datetime import timedelta
            self.next_issue_date = self.document.issue_date + timedelta(days=self.product.period_days)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.product} - {self.quantity}"

class ReceiptItem(models.Model):
    document = models.ForeignKey(ReceiptDocument, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    size = models.CharField(max_length=20, blank=True, null=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_value = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)
    
    def save(self, *args, **kwargs):
        self.total_value = self.quantity * self.unit_price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.product} - {self.quantity}"