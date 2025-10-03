from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # Company
    path("company/", views.CompanyListView.as_view(), name="company_list"),
    path("company/add/", views.CompanyCreateView.as_view(), name="company_add"),
    path(
        "company/<int:pk>/edit/",
        views.CompanyUpdateView.as_view(),
        name="company_update",
    ),
    path(
        "company/<int:pk>/delete/",
        views.CompanyDeleteView.as_view(),
        name="company_delete",
    ),
    # Department
    path("department/", views.DepartmentListView.as_view(), name="department_list"),
    path(
        "department/add/", views.DepartmentCreateView.as_view(), name="department_add"
    ),
    path(
        "department/<int:pk>/edit/",
        views.DepartmentUpdateView.as_view(),
        name="department_update",
    ),
    path(
        "department/<int:pk>/delete/",
        views.DepartmentDeleteView.as_view(),
        name="department_delete",
    ),
    # Position
    path("position/", views.PositionListView.as_view(), name="position_list"),
    path("position/add/", views.PositionCreateView.as_view(), name="position_add"),
    path(
        "position/<int:pk>/edit/",
        views.PositionUpdateView.as_view(),
        name="position_update",
    ),
    path(
        "position/<int:pk>/delete/",
        views.PositionDeleteView.as_view(),
        name="position_delete",
    ),
    # Supplier
    path("supplier/", views.SupplierListView.as_view(), name="supplier_list"),
    path("supplier/add/", views.SupplierCreateView.as_view(), name="supplier_add"),
    path(
        "supplier/<int:pk>/edit/",
        views.SupplierUpdateView.as_view(),
        name="supplier_update",
    ),
    path(
        "supplier/<int:pk>/delete/",
        views.SupplierDeleteView.as_view(),
        name="supplier_delete",
    ),
    # Product
    path("product/", views.ProductListView.as_view(), name="product_list"),
    path("product/add/", views.ProductCreateView.as_view(), name="product_add"),
    path(
        "product/<int:pk>/edit/",
        views.ProductUpdateView.as_view(),
        name="product_update",
    ),
    path(
        "product/<int:pk>/delete/",
        views.ProductDeleteView.as_view(),
        name="product_delete",
    ),
    # ProductCategory
    path("category/", views.ProductCategoryListView.as_view(), name="productcategory_list"),
    path("category/add/", views.ProductCategoryCreateView.as_view(), name="productcategory_add"),
    path(
        "category/<int:pk>/edit/",
        views.ProductCategoryUpdateView.as_view(),
        name="productcategory_update",
    ),
    path(
        "category/<int:pk>/delete/",
        views.ProductCategoryDeleteView.as_view(),
        name="productcategory_delete",
    ),
]
