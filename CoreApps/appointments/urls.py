from django.urls import path
from .views import (
    AvailabilityAPIView, 
    PublicBookingAPIView, 
    PublicReminderCreationAPIView, 
    ReminderExperienceView, # <--- NUEVA VISTA
    ReminderPatientView,    # <--- NUEVO NOMBRE PARA EL PASO 2 (Antes 3)
    ReminderSuccessView,
    CheckUserAPIView
)

urlpatterns = [
    # --- APIs ---
    path('api/availability/', AvailabilityAPIView.as_view(), name='api_availability'),
    path('api/book/', PublicBookingAPIView.as_view(), name='api_booking'),
    path('api/lead-reminder/', PublicReminderCreationAPIView.as_view(), name='api_lead_reminder'),
    path('api/check-user/', CheckUserAPIView.as_view(), name='api_check_user'),

    # --- WIZARD PÚBLICO (NUEVA ESTRUCTURA 2 PASOS) ---
    # Paso 1: Experiencia (Medicamento + Enfermero + Rating)
    path('recordatorio/experiencia/', ReminderExperienceView.as_view(), name='public_reminder_experience'),
    
    # Paso 2: Datos Paciente (Antes Paso 3)
    path('recordatorio/paciente/', ReminderPatientView.as_view(), name='public_reminder_patient'),
    
    # Éxito
    path('recordatorio/exito/', ReminderSuccessView.as_view(), name='public_reminder_success'),
]