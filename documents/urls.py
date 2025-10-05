from django.urls import path
from . import views

app_name = "documents"

urlpatterns = [
    path("dw/", views.DWListView.as_view(), name="dw_list"),
    path("pz/", views.PZListView.as_view(), name="pz_list"),

    path("dw/create/", views.IssueCreateView.as_view(), name="create_dw"),
    path("pz/create/", views.ReceiptCreateView.as_view(), name="create_pz"),

    path("dw/<int:pk>/", views.DWDetailView.as_view(), name="dw_detail"),
    path("pz/<int:pk>/", views.PZDetailView.as_view(), name="pz_detail"),

    path("dw/<int:pk>/edit/", views.DocumentEditView.as_view(), name="edit_dw"),
    path("pz/<int:pk>/edit/", views.DocumentEditView.as_view(), name="edit_pz"),

    path("item/<int:item_id>/mark_used/", views.ItemMarkUsedView.as_view(), name="item_mark_used"),
    path("item/<int:item_id>/delete/<str:kind>/", views.ItemDeleteView.as_view(), name="item_delete"),
]

