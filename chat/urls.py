from django.urls import path
from .views import (
    ConversationCreateView,
    ConversationDetailView,
    SendMessageView,
    ClearConversationView,
    ConversationStatsView,
    SystemStatusView
)

urlpatterns = [
    path('api/v1/status/', SystemStatusView.as_view(), name='system-status'),
    path('api/v1/conversations/create/', ConversationCreateView.as_view(), name='conversation-create'),
    path('api/v1/conversations/<str:session_id>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('api/v1/conversations/<str:session_id>/stats/', ConversationStatsView.as_view(), name='conversation-stats'),
    path('api/v1/conversations/<str:session_id>/clear/', ClearConversationView.as_view(), name='conversation-clear'),    
    path('api/v1/conversations/<str:session_id>/send-message/', SendMessageView.as_view(), name='send-message'),
]