from django.urls import path, include
from . import views

app_name = "documents"

urlpatterns = [
    path("api/" , include("documents.api.urls")),
    path("dw/", views.DWListView.as_view(), name="dw_list"),
    path("pz/", views.PZListView.as_view(), name="pz_list"),

    path("dw/create/", views.IssueCreateView.as_view(), name="create_dw"),
    path("pz/create/", views.ReceiptCreateView.as_view(), name="create_pz"),

    path("dw/<int:pk>/", views.DWDetailView.as_view(), name="dw_detail"),
    path("pz/<int:pk>/", views.PZDetailView.as_view(), name="pz_detail"),

    path("dw/<int:pk>/edit/", views.DWEditView.as_view(), name="edit_dw"),
    path("pz/<int:pk>/edit/", views.PZEditView.as_view(), name="edit_pz"),

    path("item/<int:item_id>/mark_used/", views.ItemMarkUsedView.as_view(), name="item_mark_used"),
    path("item/<int:item_id>/delete/<str:kind>/", views.ItemDeleteView.as_view(), name="item_delete"),

    path("pending/", views.PendingReceiptListView.as_view(), name="pending_receipt_list"),
    path("pending/<int:pk>/", views.PendingReceiptDetailView.as_view(), name="pending_receipt_detail"),
    path("pending/delete/<int:pk>/", views.PendingReceiptDeleteView.as_view(), name="pending_receipt_delete"),

    path("invoices/", views.InvoiceListView.as_view(), name="invoice_list"),
    path("invoices/<int:pk>/", views.InvoiceDetailView.as_view(), name="invoice_detail"),
]