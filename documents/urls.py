from django.urls import path
from .views import DocumentUploadView, DocumentAgentQueryView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("api/v1/upload/", DocumentUploadView.as_view(), name="document-upload"),
    path("api/v1/query/<session_id>/", DocumentAgentQueryView.as_view(), name="document-query"),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
