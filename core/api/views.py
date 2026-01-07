from core.api.serializer import FlexibleInvoiceSerializer
from core.models import PendingProduct, Product, ProductCategory
from documents.models import InvoiceDocument, InvoiceLineItem
from decimal import Decimal, InvalidOperation
from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response


class InvoiceToPendingProductsAPIView(generics.GenericAPIView):
    serializer_class = FlexibleInvoiceSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        items = serializer.validated_data.get("items", [])
        order_number = request.data.get("invoice", {}).get("order_number", "unknown")

        invoice_doc, _ = InvoiceDocument.objects.get_or_create(order_number=order_number)
        default_category, _ = ProductCategory.objects.get_or_create(name="clothing")

        # 1. Збираємо всі коди
        codes = [
            item.get("code") or item.get("sku")
            for item in items
            if item.get("code") or item.get("sku")
        ]

        # 2. Отримуємо всі існуючі продукти одним запитом
        existing_products = {
            p.code: p for p in Product.objects.filter(code__in=codes)
        }

        pending_products_to_create = []
        pending_by_code = {}
        line_items_to_create = []

        for item in items:
            code = item.get("code") or item.get("sku")
            if not code:
                continue

            quantity = item.get("quantity", 0)
            name = item.get("name") or item.get("product_name") or "Unnamed"
            size = item.get("size") or ""
            description = item.get("description") or ""

            raw_price = item.get("unit_price") or item.get("price") or "0"
            try:
                unit_price = Decimal(str(raw_price).replace(",", "."))
            except InvalidOperation:
                unit_price = Decimal("0")

            product = existing_products.get(code)

            if product:
                line_items_to_create.append(
                    InvoiceLineItem(
                        document=invoice_doc,
                        product=product,
                        code=product.code,
                        quantity_ordered=quantity,
                        quantity_delivered=0,
                    )
                )
            else:
                pending = PendingProduct(
                    code=code,
                    name=name,
                    unit_price=unit_price,
                    category=default_category,
                    description=description,
                    size=size,
                )
                pending_products_to_create.append(pending)
                pending_by_code[code] = (pending, quantity)

        # 4. bulk_create PendingProduct
        created_pending = PendingProduct.objects.bulk_create(
            pending_products_to_create
        )

        # 5. Створюємо InvoiceLineItem для PendingProduct
        for pending in created_pending:
            quantity = pending_by_code[pending.code][1]
            line_items_to_create.append(
                InvoiceLineItem(
                    document=invoice_doc,
                    pending_product=pending,
                    product=None,
                    code=pending.code,
                    quantity_ordered=quantity,
                    quantity_delivered=0,
                )
            )

        InvoiceLineItem.objects.bulk_create(line_items_to_create)

        return Response(
            {
                "status": "ok",
                "created_pending_products": [p.code for p in created_pending],
                "used_existing_products": list(existing_products.keys()),
            },
            status=status.HTTP_201_CREATED,
        )
