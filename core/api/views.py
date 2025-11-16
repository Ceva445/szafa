from rest_framework.response import Response
from rest_framework import status, generics
from core.api.serializer import FlexibleInvoiceSerializer
from core.models import PendingProduct, ProductCategory
from decimal import Decimal, InvalidOperation
from django.db import transaction


class InvoiceToPendingProductsAPIView(generics.GenericAPIView):
    serializer_class = FlexibleInvoiceSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        items = serializer.validated_data.get("items", [])

        default_category, _ = ProductCategory.objects.get_or_create(name="clothing")

        products_to_create = []

        for item in items:
            code = item.get("code") or item.get("sku")
            if not code:
                continue

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

        return Response(
            {"status": "ok", "created_products": created_ids},
            status=status.HTTP_201_CREATED,
        )
