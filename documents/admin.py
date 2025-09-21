from django.contrib import admin
from .models import IssueDocument, ReceiptDocument, DocumentItem, ReceiptItem


class DocumentItemInline(admin.TabularInline):
    model = DocumentItem
    extra = 1
    fields = ["product", "quantity", "size", "notes", "status"]
    readonly_fields = ["next_issue_date"]


class ReceiptItemInline(admin.TabularInline):
    model = ReceiptItem
    extra = 1
    fields = ["product", "quantity", "size", "unit_price", "total_value", "notes"]
    readonly_fields = ["total_value"]


@admin.register(IssueDocument)
class IssueDocumentAdmin(admin.ModelAdmin):
    list_display = ["document_number", "employee", "issue_date", "created_at"]
    list_filter = ["issue_date", "created_at"]
    search_fields = ["document_number", "employee__first_name", "employee__last_name"]
    date_hierarchy = "issue_date"
    inlines = [DocumentItemInline]


@admin.register(ReceiptDocument)
class ReceiptDocumentAdmin(admin.ModelAdmin):
    list_display = [
        "document_number",
        "supplier",
        "recipient",
        "issue_date",
        "created_at",
    ]
    list_filter = ["supplier", "recipient", "issue_date"]
    search_fields = ["document_number", "supplier__name", "recipient__name"]
    date_hierarchy = "issue_date"
    inlines = [ReceiptItemInline]


@admin.register(DocumentItem)
class DocumentItemAdmin(admin.ModelAdmin):
    list_display = [
        "document",
        "product",
        "quantity",
        "size",
        "status",
        "next_issue_date",
    ]
    list_filter = ["status", "product__category"]
    search_fields = ["document__document_number", "product__code", "product__name"]
    readonly_fields = ["next_issue_date"]


@admin.register(ReceiptItem)
class ReceiptItemAdmin(admin.ModelAdmin):
    list_display = [
        "document",
        "product",
        "quantity",
        "size",
        "unit_price",
        "total_value",
    ]
    list_filter = ["product__category"]
    search_fields = ["document__document_number", "product__code", "product__name"]
    readonly_fields = ["total_value"]
