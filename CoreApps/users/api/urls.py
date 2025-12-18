from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    MyTokenObtainPairView, 
    UserProfileView, 
    PatientCreateAPIView, 
    NurseCreateAPIView,
    PatientListAPIView, # Nuevo
    NurseListAPIView    # Nuevo
)

urlpatterns = [
    path('auth/login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', UserProfileView.as_view(), name='user_profile'),
    
    # Endpoints de Lectura (Listados)
    path('users/patients/', PatientListAPIView.as_view(), name='api_patient_list'),
    path('users/nurses/', NurseListAPIView.as_view(), name='api_nurse_list'),

    # Endpoints de Creación
    path('users/patients/create/', PatientCreateAPIView.as_view(), name='api_patient_create'),
    path('users/nurses/create/', NurseCreateAPIView.as_view(), name='api_nurse_create'),
]
