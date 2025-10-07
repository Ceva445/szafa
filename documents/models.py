from datetime import date
from django.db import models
from core.models import Product, Supplier, Company
from employees.models import Employee


class DocumentBase(models.Model):
    # Provides common fields and structure for all document types
    DOCUMENT_TYPES = [
        ("DW", "Dokument Wydania"),
        ("PZ", "Przyjęcie Zewnętrzne"),
    ]

    document_type = models.CharField(max_length=2, choices=DOCUMENT_TYPES)
    document_number = models.CharField(max_length=50, unique=True)
    issue_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class IssueDocument(DocumentBase):
    # Tracks items issued to specific employees with automatic numbering
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT)

    def save(self, *args, **kwargs):
        if not self.document_number:
            year = self.issue_date.year
            month = self.issue_date.month
            last_doc = (
                IssueDocument.objects.filter(
                    issue_date__year=year, issue_date__month=month
                )
                .order_by("-id")
                .first()
            )

            index = 1
            if last_doc:
                index = int(last_doc.document_number.split("/")[-1]) + 1

            self.document_number = f"DW/{year}/{month:02d}/{index:04d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.document_number


class ReceiptDocument(DocumentBase):
    # Records incoming items from suppliers to companies with automatic numbering
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    recipient = models.ForeignKey(Company, on_delete=models.PROTECT)

    def save(self, *args, **kwargs):
        if not self.document_number:
            year = self.issue_date.year
            month = self.issue_date.month
            last_doc = (
                ReceiptDocument.objects.filter(
                    issue_date__year=year, issue_date__month=month
                )
                .order_by("-id")
                .first()
            )

            index = 1
            if last_doc:
                index = int(last_doc.document_number.split("/")[-1]) + 1

            self.document_number = f"PZ/{year}/{month:02d}/{index:04d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.document_number


class DocumentItem(models.Model):
    ITEM_STATUS = [
        ("active", "Aktywny"),
        ("used", "Zużyty"),
        ("returned", "Zwrócony"),
    ]

    document = models.ForeignKey(
        IssueDocument, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    total_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, editable=False)
    size = models.CharField(max_length=20, blank=True, null=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=ITEM_STATUS, default="active")
    next_issue_date = models.DateField(blank=True, null=True)
    auto_deactivated = models.BooleanField(
        default=False,
        help_text="Was automatically deactivated due to employment termination",
    )

    class Meta:
        ordering = ["-document__issue_date"]

    def __str__(self):
        return f"{self.product} - {self.quantity} ({self.status})"

    def save(self, *args, **kwargs):
        # Automatic calculation of total_value
        if self.quantity is not None and self.unit_price is not None:
            self.total_value = self.quantity * self.unit_price
        else:
            self.total_value = None

        # Automatic calculation of the next issue date
        if not self.next_issue_date and self.document.issue_date:
            from datetime import timedelta

            self.next_issue_date = self.document.issue_date + timedelta(
                days=self.product.period_days
            )

        # Check if the employee is still employed
        if self.status == "active":
            employee = self.document.employee
            current_period = employee.get_current_employment_period()

            if (
                current_period
                and current_period.end_date
                and current_period.end_date <= date.today()
            ):
                self.status = "used"
                self.auto_deactivated = True

        super().save(*args, **kwargs)

    def mark_as_used(self):
        """Mark product as used"""
        self.status = "used"
        self.save()

    def return_to_warehouse(self):
        """Return product to warehouse"""
        from warehouse.signals import return_product_to_warehouse

        return_product_to_warehouse(self)
        self.status = "returned"
        self.save()


class ReceiptItem(models.Model):
    # Records specific products received from suppliers, including pricing and quantities
    document = models.ForeignKey(
        ReceiptDocument, on_delete=models.CASCADE, related_name="items"
    )
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
