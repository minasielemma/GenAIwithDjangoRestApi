from django.urls import path
from .views import DocumentUploadView, DocumentAgentQueryView

urlpatterns = [
    path("api/v1/upload/", DocumentUploadView.as_view(), name="document-upload"),
    path("api/v1/query/<session_id>/", DocumentAgentQueryView.as_view(), name="document-query"),
]
