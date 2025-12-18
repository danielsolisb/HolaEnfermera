from rest_framework import viewsets, permissions, filters
from CoreApps.services.models import Service, Medication, ServiceCategory
from .serializers import ServiceSerializer, MedicationSerializer, ServiceCategorySerializer

class ServiceViewSet(viewsets.ModelViewSet):
    """
    CRUD completo de Servicios.
    """
    queryset = Service.objects.all().order_by('categoria', 'nombre')
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'descripcion']

class MedicationViewSet(viewsets.ModelViewSet):
    """
    CRUD completo de Medicamentos.
    """
    queryset = Medication.objects.all().order_by('nombre')
    serializer_class = MedicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'descripcion']

class ServiceCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Solo lectura para categorías (se usan en dropdowns).
    """
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
