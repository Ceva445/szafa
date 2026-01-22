from rest_framework.response import Response
from core.api.serializer import FlexibleInvoiceSerializer
from core.models import Product, Supplier, Company
from rest_framework import status, generics
from django.db import transaction
from datetime import datetime
 
from documents.models import PendingReceiptDocument, PendingReceiptItem

class PendingDocumentImportAPIView(generics.GenericAPIView):
    serializer_class = FlexibleInvoiceSerializer

    def parse_date(self, date_str):
        """Parse date from various formats to YYYY-MM-DD"""
        if not date_str:
            return None
        
        try:
            # Try DD.MM.YYYY format
            if '.' in date_str:
                date_obj = datetime.strptime(date_str, "%d.%m.%Y")
                return date_obj.date()
            # Try YYYY-MM-DD format
            elif '-' in date_str:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                return date_obj.date()
            # Try DD/MM/YYYY format
            elif '/' in date_str:
                date_obj = datetime.strptime(date_str, "%d/%m/%Y")
                return date_obj.date()
            else:
                # return today if format is unrecognized
                return datetime.today().date()
        except (ValueError, TypeError):
            return None

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        items = data.get("items", [])
        
        suplier_str = data.get("seller", {}).get("name", "").split()[0].lower()
        
        # Parse dates before creating the document
        order_date = self.parse_date(data.get("dates", {}).get("order_date"))
        delivery_date = self.parse_date(data.get("dates", {}).get("delivery_date"))
        
        pending_doc = PendingReceiptDocument.objects.create(
            supplier=Supplier.objects.filter(name__iexact=suplier_str).first(),
            recipient=Company.objects.filter(name="Ceva 1").first(),
            issue_date=order_date,
            delivery_date=delivery_date,
            reference_number=data.get("reference_number"),
            document_number=data.get("document_number"),
            order_number=data.get("order_number"),
        )

        pending_items = []
        for item in items:
            code = item.get("code")

            product = None
            if code:
                product = Product.objects.filter(code=code).first()

            pending_items.append(
                PendingReceiptItem(
                    document=pending_doc,
                    code=code,
                    name=item.get("name", "") or "",
                    quantity_ordered=item.get("quantity_ordered") or 0,
                    quantity_delivered=item.get("quantity_delivered") or 0,
                    product=product, 
                )
            )

        PendingReceiptItem.objects.bulk_create(pending_items)

        return Response(
            {
                "status": "ok",
                "pending_document_id": pending_doc.id,
                "items_created": len(pending_items)
            },
            status=status.HTTP_201_CREATED,
        )