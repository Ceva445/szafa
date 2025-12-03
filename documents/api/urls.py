from django.urls import path, include
from documents.api.views import PendingDocumentImportAPIView
urlpatterns = [
    path(
        "documents/pending/create/", PendingDocumentImportAPIView.as_view(), name="pending-document-create"
    )
]