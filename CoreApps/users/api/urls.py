from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import MyTokenObtainPairView, UserProfileView

urlpatterns = [
    path('auth/login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', UserProfileView.as_view(), name='user_profile'),
]
