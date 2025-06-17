from django.urls import path
from timesheet_app.views.auth_views import (
    CustomTokenObtainPairView,RefreshTokenView, LogoutView, AuthCheckView,
    RequestPasswordResetCodeView, ChangePasswordView, RegisterUserView
)

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/',RefreshTokenView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('auth-check/', AuthCheckView.as_view(), name='auth-check'),
    path('register/', RegisterUserView.as_view(), name='register_user'),
    path('request-password-reset-code/', RequestPasswordResetCodeView.as_view(), name='request_password_reset_code'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
]
