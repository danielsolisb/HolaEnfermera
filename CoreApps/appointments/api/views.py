from rest_framework import viewsets, filters, permissions
from django_filters.rest_framework import DjangoFilterBackend
from CoreApps.appointments.models import AppointmentReminder
from .serializers import LeadSerializer

class LeadViewSet(viewsets.ModelViewSet):
    """
    API para gestionar Recordatorios/Leads.
    Permite Listar, Ver Detalle y Actualizar (PATCH).
    No permite Crear ni Borrar por ahora (se crean por sistema o web pública).
    """
    serializer_class = LeadSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch', 'head', 'options'] # Restringimos a solo lectura y edición parcial
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Filtros
    filterset_fields = ['estado', 'origen']
    search_fields = ['paciente__first_name', 'paciente__last_name', 'paciente__cedula', 'medicamento_catalogo__nombre']
    ordering_fields = ['fecha_limite_sugerida', 'fecha_creacion']
    ordering = ['fecha_limite_sugerida'] # Por defecto: los más urgentes primero

    def get_queryset(self):
        # Optimizamos queries con select_related
        return AppointmentReminder.objects.all().select_related(
            'paciente', 'medicamento_catalogo', 'servicio_sugerido'
        )
