# warehouse/management/commands/update_stockmovement_document_numbers.py
from django.core.management.base import BaseCommand
from django.db import transaction
from documents.models import IssueDocument, ReceiptDocument
from warehouse.models import StockMovement


class Command(BaseCommand):
    help = "Update existing StockMovement records with document numbers"

    def handle(self, *args, **options):
        self.stdout.write(
            "Starting to update StockMovement records with document numbers..."
        )

        updated_count = 0

        with transaction.atomic():

            dw_movements = StockMovement.objects.filter(document_type="DW")
            for movement in dw_movements:
                try:
                    document = IssueDocument.objects.get(id=movement.document_id)
                    movement.document_number = document.document_number
                    movement.save()
                    updated_count += 1
                except IssueDocument.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"IssueDocument with id {movement.document_id} not found"
                        )
                    )

            pz_movements = StockMovement.objects.filter(document_type="PZ")
            for movement in pz_movements:
                try:
                    document = ReceiptDocument.objects.get(id=movement.document_id)
                    movement.document_number = document.document_number
                    movement.save()
                    updated_count += 1
                except ReceiptDocument.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"ReceiptDocument with id {movement.document_id} not found"
                        )
                    )

            return_movements = StockMovement.objects.filter(document_type="RETURN")
            for movement in return_movements:
                try:
                    document = IssueDocument.objects.get(id=movement.document_id)
                    movement.document_number = document.document_number
                    movement.save()
                    updated_count += 1
                except IssueDocument.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"IssueDocument for RETURN with id {movement.document_id} not found"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully updated {updated_count} StockMovement records"
            )
        )
