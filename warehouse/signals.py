# warehouse/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from documents.models import DocumentItem, ReceiptDocument, IssueDocument
from warehouse.models import StockMovement, WarehouseStock


@receiver(post_save, sender="documents.ReceiptItem")
def update_stock_on_receipt(sender, instance, created, **kwargs):
    """Updating the composition when creating a PZ"""
    if created:
        warehouse_stock, created = WarehouseStock.objects.get_or_create(
            product=instance.product, size=instance.size, defaults={"quantity": 0}
        )
        warehouse_stock.update_stock(instance.quantity)

        # Record in the history of movements
        StockMovement.objects.create(
            product=instance.product,
            size=instance.size,
            movement_type="in",
            quantity=instance.quantity,
            document_type="PZ",
            document_id=instance.document.id,
            document_number=instance.document.document_number,
            notes=f"External reception : {instance.document.document_number}",
        )


@receiver(post_save, sender="documents.DocumentItem")
def update_stock_on_issue(sender, instance, created, **kwargs):
    """Updating the stock when creating a DW"""
    if created and instance.status == "active":
        warehouse_stock, created = WarehouseStock.objects.get_or_create(
            product=instance.product, size=instance.size, defaults={"quantity": 0}
        )
        warehouse_stock.update_stock(-instance.quantity)

        # Record in the history of movements
        StockMovement.objects.create(
            product=instance.product,
            size=instance.size,
            movement_type="out",
            quantity=instance.quantity,
            document_type="DW",
            document_id=instance.document.id,
            document_number=instance.document.document_number,
            notes=f"Employee issuance: {instance.document.employee}",
        )


@receiver(post_save, sender="documents.DocumentItem")
def update_stock_on_status_change(sender, instance, **kwargs):
    """Updating the stock when changing the status of the item"""
    if instance.pk:
        old_instance = DocumentItem.objects.get(pk=instance.pk)

        # If the product is returned to the warehouse
        if old_instance.status != "returned" and instance.status == "returned":
            warehouse_stock, created = WarehouseStock.objects.get_or_create(
                product=instance.product, size=instance.size, defaults={"quantity": 0}
            )
            warehouse_stock.update_stock(instance.quantity)

            StockMovement.objects.create(
                product=instance.product,
                size=instance.size,
                movement_type="in",
                quantity=instance.quantity,
                document_type="RETURN",
                document_id=instance.document.id,
                document_number=instance.document.document_number,
                notes=f"Return from employee: {instance.document.employee}",
            )