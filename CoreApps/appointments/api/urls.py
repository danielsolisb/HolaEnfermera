from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LeadViewSet, LeadCreateAPIView

router = DefaultRouter()
router.register(r'', LeadViewSet, basename='api_leads')

urlpatterns = [
    # Es importante poner 'create/' ANTES del router para que no lo confunda con un ID
    path('create/', LeadCreateAPIView.as_view(), name='api_leads_create'),
    path('', include(router.urls)),
]
