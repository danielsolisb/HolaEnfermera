from django.urls import path
from .views import (
    AvailabilityAPIView, 
    PublicBookingAPIView, 
    PublicReminderCreationAPIView, 
    ReminderExperienceView, # <--- NUEVA VISTA
    ReminderPatientView,    # <--- NUEVO NOMBRE PARA EL PASO 2 (Antes 3)
    ReminderSuccessView,
    CheckUserAPIView,
    AdminReminderListView,
    AdminReminderUpdateView,
    AdminReminderCreateView,
    AdminReminderDeleteView,
    AdminReminderStatusAPI
)

urlpatterns = [
    # --- APIs ---
    path('api/availability/', AvailabilityAPIView.as_view(), name='api_availability'),
    path('api/book/', PublicBookingAPIView.as_view(), name='api_booking'),
    path('api/lead-reminder/', PublicReminderCreationAPIView.as_view(), name='api_lead_reminder'),
    path('api/check-user/', CheckUserAPIView.as_view(), name='api_check_user'),

    path('dashboard/recordatorios/eliminar/<int:pk>/', AdminReminderDeleteView.as_view(), name='admin_reminder_delete'),
    path('api/recordatorios/cambiar-estado/', AdminReminderStatusAPI.as_view(), name='api_reminder_status'),

    # --- WIZARD PÚBLICO (NUEVA ESTRUCTURA 2 PASOS) ---
    # Paso 1: Experiencia (Medicamento + Enfermero + Rating)
    path('recordatorio/experiencia/', ReminderExperienceView.as_view(), name='public_reminder_experience'),
    
    # Paso 2: Datos Paciente (Antes Paso 3)
    path('recordatorio/paciente/', ReminderPatientView.as_view(), name='public_reminder_patient'),
    
    # Éxito
    path('recordatorio/exito/', ReminderSuccessView.as_view(), name='public_reminder_success'),

    # --- GESTIÓN ADMINISTRATIVA (FASE 1) ---
    path('dashboard/recordatorios/', AdminReminderListView.as_view(), name='admin_reminder_list'),
    path('dashboard/recordatorios/crear/', AdminReminderCreateView.as_view(), name='admin_reminder_create'),
    path('dashboard/recordatorios/editar/<int:pk>/', AdminReminderUpdateView.as_view(), name='admin_reminder_update'),
]