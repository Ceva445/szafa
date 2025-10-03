from django.urls import path
from . import views

app_name = "documents"

urlpatterns = [
    path("", views.DocumentsListView.as_view(), name="list"),
    path("dw/create/", views.IssueCreateView.as_view(), name="create_dw"),
    path("pz/create/", views.ReceiptCreateView.as_view(), name="create_pz"),
    path(
        "<int:pk>/<str:kind>/", views.DocumentDetailView.as_view(), name="detail"
    ),  # kind 'dw'|'pz'
    path("<int:pk>/edit/<str:kind>/", views.DocumentEditView.as_view(), name="edit"),
    path(
        "item/<int:item_id>/mark_used/",
        views.ItemMarkUsedView.as_view(),
        name="item_mark_used",
    ),
    path(
        "item/<int:item_id>/delete/<str:kind>/",
        views.ItemDeleteView.as_view(),
        name="item_delete",
    ),
]
