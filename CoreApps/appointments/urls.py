from django.urls import path
from .views import AvailabilityAPIView, PublicBookingAPIView, PublicReminderCreationAPIView, LeadReminderWizardView, ReminderStep1View, ReminderStep2View, ReminderStep3View, ReminderSuccessView

urlpatterns = [
    # Rutas API (para consumo del Frontend/JS)
    path('api/availability/', AvailabilityAPIView.as_view(), name='api_availability'),
    path('api/book/', PublicBookingAPIView.as_view(), name='api_booking'),

    path('api/lead-reminder/', PublicReminderCreationAPIView.as_view(), name='api_lead_reminder'),

    #path('recordatorio-medicamento/', LeadReminderWizardView.as_view(), name='public_reminder_wizard'),

    path('recordatorio/paso-1/', ReminderStep1View.as_view(), name='public_reminder_step1'),
    path('recordatorio/paso-2/', ReminderStep2View.as_view(), name='public_reminder_step2'),
    path('recordatorio/paso-3/', ReminderStep3View.as_view(), name='public_reminder_step3'),
    path('recordatorio/exito/', ReminderSuccessView.as_view(), name='public_reminder_success'),
]