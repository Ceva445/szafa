from django.core.management.base import BaseCommand

from documents.models import DocumentItem


class Command(BaseCommand):
    help = "Update total_value for all existing DocumentItem records"

    def handle(self, *args, **options):
        items = DocumentItem.objects.all()
        for item in items:
            if item.quantity is not None and item.product.unit_price is not None:
                item.total_value = item.quantity * item.product.unit_price
                item.unit_price = item.product.unit_price
            else:
                item.total_value = None
                item.unit_price = None
            item.save(update_fields=["total_value", "unit_price"])

        self.stdout.write(
            self.style.SUCCESS(f"Successfully updated {items.count()} records")
        )
