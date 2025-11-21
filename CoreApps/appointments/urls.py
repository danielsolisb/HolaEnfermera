from django.urls import path
from .views import AvailabilityAPIView, PublicBookingAPIView

urlpatterns = [
    # Rutas API (para consumo del Frontend/JS)
    path('api/availability/', AvailabilityAPIView.as_view(), name='api_availability'),
    path('api/book/', PublicBookingAPIView.as_view(), name='api_booking'),
]