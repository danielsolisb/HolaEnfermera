from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import CustomLoginView, PublicNurseListAPIView, QuickCreatePatientView
from .views import PatientListView, PatientCreateView, PatientUpdateView, NurseListView, NurseCreateView, NurseUpdateView
urlpatterns = [
    # La ruta es vacía aquí porque la incluiremos con el prefijo 'login/' en el config principal, 
    # O podemos definirla explícitamente aquí. 
    # Para cumplir tu requisito de "localhost:8000/login":
    
    path('login/', CustomLoginView.as_view(), name='login'),
    
    # Aprovechamos para dejar listo el logout
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),

    path('api/nurses/', PublicNurseListAPIView.as_view(), name='api_nurses_list'),

    path('api/quick-create-patient/', QuickCreatePatientView.as_view(), name='api_quick_create_patient'),

    # PACIENTES
    path('dashboard/pacientes/', PatientListView.as_view(), name='admin_patient_list'),
    path('dashboard/pacientes/nuevo/', PatientCreateView.as_view(), name='admin_patient_create'),
    path('dashboard/pacientes/editar/<int:pk>/', PatientUpdateView.as_view(), name='admin_patient_update'),

    # ENFERMEROS
    path('dashboard/personal/', NurseListView.as_view(), name='admin_nurse_list'),
    path('dashboard/personal/nuevo/', NurseCreateView.as_view(), name='admin_nurse_create'),
    path('dashboard/personal/editar/<int:pk>/', NurseUpdateView.as_view(), name='admin_nurse_update'),
]