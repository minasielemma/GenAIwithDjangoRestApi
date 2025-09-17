from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView
from django.urls import path

from user_auth.views import ChangePasswordApiView, GetUserAccountView, UserRegistrationView

urlpatterns = [
    path('api/v1/register/', UserRegistrationView.as_view(), name='register'),
    path('api/v1/token/', TokenObtainPairView.as_view(), name='login'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/user/', GetUserAccountView.as_view(), name='get-user-account'),
    path('api/v1/change_password/', ChangePasswordApiView.as_view(), name='change_password'),
]