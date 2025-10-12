from django.urls import path, include

from . import views

urlpatterns = [
    path("", views.ReportsView.as_view(), name="main"),
]

app_name = "reports"
