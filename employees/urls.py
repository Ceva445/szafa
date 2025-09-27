from django.urls import path, include

from .views import (
    AddEmployeeView,
    DeleteEmployeeView,
    EditEmployeeView,
    EmployeesListView,
    EmployeeDetailView,
)


urlpatterns = [
    path("", EmployeesListView.as_view(), name="list"),
    path("add/", AddEmployeeView.as_view(), name="add"),
    path("<int:pk>/", EmployeeDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", EditEmployeeView.as_view(), name="edit"),
    path("<int:pk>/delete/", DeleteEmployeeView.as_view(), name="delete"),
]


app_name = "employees"
