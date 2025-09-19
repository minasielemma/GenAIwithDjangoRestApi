from django.urls import path

from api_with_mcp.views import EmailAnalysisView


urlpatterns = [
    path('api/v1/email_analyzer/', EmailAnalysisView.as_view(), name='email_analyzer'),
]