from django.urls import path

from weather_Agent.views import WeatherAgentQueryView

urlpatterns = [
    path('api/v1/weather_analysis/<session_id>/', WeatherAgentQueryView.as_view(), name='weather_analysis'),
]