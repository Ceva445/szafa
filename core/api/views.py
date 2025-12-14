from rest_framework.response import Response
from rest_framework import status, generics
from core.api.serializer import FlexibleInvoiceSerializer
from core.models import PendingProduct, ProductCategory
from documents.models import InvoiceDocument, InvoiceLineItem
from decimal import Decimal, InvalidOperation
from django.db import transaction
from rest_framework.permissions import IsAuthenticated


class InvoiceToPendingProductsAPIView(generics.GenericAPIView):
    serializer_class = FlexibleInvoiceSerializer
    #permission_classes = [IsAuthenticated] # додати аутентифікацію пізніше

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        items = serializer.validated_data.get("items", [])
        order_number = request.data.get("invoice", {}).get("order_number", "unknown")
        invoice_doc = InvoiceDocument.objects.get_or_create(order_number=order_number)[0]

        default_category, _ = ProductCategory.objects.get_or_create(name="clothing")

        products_to_create = []
        item_info = {}

        for item in items:
            code = item.get("code") or item.get("sku")
            if not code:
                continue

            item_info[code] = item.get("quantity", 0)

            name = item.get("name") or item.get("product_name") or "Unnamed"

            raw_price = item.get("unit_price") or item.get("price") or "0"
            try:
                unit_price = Decimal(str(raw_price).replace(",", "."))
            except InvalidOperation:
                unit_price = Decimal("0")

            size = item.get("size") or ""
            description = item.get("description") or ""

            products_to_create.append(
                PendingProduct(
                    code=code,
                    name=name,
                    unit_price=unit_price,
                    category=default_category,
                    description=description,
                    size=size,
                )
            )

        created_objects = PendingProduct.objects.bulk_create(products_to_create)
        created_ids = [obj.code for obj in created_objects]
        invoise_line_to_create = []
        for pending_product in created_objects:
            invoise_line_to_create.append(
                InvoiceLineItem(
                    document=invoice_doc,
                    pending_product=pending_product,
                    code=pending_product.code,
                    quantity_ordered=item_info.get(pending_product.code, 0),
                    quantity_delivered=0,
                    date_recieved=None,
                )
            )
        InvoiceLineItem.objects.bulk_create(invoise_line_to_create)

        return Response(
            {"status": "ok", "created_products": created_ids},
            status=status.HTTP_201_CREATED,
        )
