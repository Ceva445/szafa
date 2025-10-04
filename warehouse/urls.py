from django.urls import path
from . import views

app_name = "warehouse"

urlpatterns = [
    path("", views.WarehouseListView.as_view(), name="list"),
    path("stock/<int:pk>/", views.WarehouseDetailView.as_view(), name="detail"),
    path("stock/<int:pk>/history/", views.StockHistoryView.as_view(), name="history"),
]
