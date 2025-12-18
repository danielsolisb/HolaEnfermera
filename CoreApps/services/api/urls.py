from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceViewSet, MedicationViewSet, ServiceCategoryViewSet

router = DefaultRouter()
router.register(r'services', ServiceViewSet, basename='api_services')
router.register(r'medications', MedicationViewSet, basename='api_medications')
router.register(r'categories', ServiceCategoryViewSet, basename='api_categories')

urlpatterns = [
    path('', include(router.urls)),
]
