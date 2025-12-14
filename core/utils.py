from core.models import Product
from documents.models import InvoiceLineItem
from django.db import transaction
import logging
    

def replace_pending_products_safe():
    try:
        with transaction.atomic():
        
            line_items = InvoiceLineItem.objects.filter(
                product__isnull=True,
                pending_product__isnull=False
            ).select_related('pending_product').iterator(chunk_size=1000)

            pending_codes_set = set()
            items_map = {}
            
            for item in line_items:
                if item.pending_product:
                    pending_codes_set.add(item.pending_product.code)
                    items_map[item.id] = item

            existing_products = Product.objects.filter(
                code__in=pending_codes_set
            ).in_bulk(field_name='code')            
            update_batch = []
            updated_count = 0
            
            for item_id, item in items_map.items():
                product_code = item.pending_product.code
                if product_code in existing_products:
                    update_batch.append(
                        InvoiceLineItem(
                            id=item_id,
                            product=existing_products[product_code],
                            pending_product=None
                        )
                    )
                    updated_count += 1

                    if len(update_batch) >= 500:
                        InvoiceLineItem.objects.bulk_update(
                            update_batch,
                            ['product', 'pending_product']
                        )
                        update_batch = []
                        
            if update_batch:
                InvoiceLineItem.objects.bulk_update(
                    update_batch,
                    ['product', 'pending_product']
                )
            return updated_count
            
    except Exception as e:
        print(f"Error replacing pending_product: {str(e)}")
        raise