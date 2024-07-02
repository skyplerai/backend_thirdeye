from django.urls import path
from .views import (
    RegisterView,
    VerifyEmail,
    LoginAPIView,
    RequestPasswordResetEmail,
    SetNewPasswordWithOTPView,
    GoogleSignInView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-email/', VerifyEmail.as_view(), name='verify-email'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('request-reset-password/', RequestPasswordResetEmail.as_view(), name='request-reset-password'),
    path('reset-password/', SetNewPasswordWithOTPView.as_view(), name='reset-password'),
    path('google-sign-in/', GoogleSignInView.as_view(), name='google-sign-in'),
]
