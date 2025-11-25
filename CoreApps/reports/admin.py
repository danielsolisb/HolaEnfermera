from django.contrib import admin
from .models import ServiceReport, ServiceFeedback

@admin.register(ServiceReport)
class ServiceReportAdmin(admin.ModelAdmin):
    list_display = ('cita', 'registrado_por', 'requiere_seguimiento', 'fecha_registro')
    list_filter = ('requiere_seguimiento', 'fecha_registro')
    search_fields = ('cita__paciente__cedula', 'cita__id')
    
    fieldsets = (
        ('Cita Vinculada', {
            'fields': ('cita', 'registrado_por')
        }),
        ('Ejecución', {
            'fields': ('observaciones_tecnicas', 'foto_evidencia', 'firma_paciente_digital')
        }),
        ('Estrategia de Cierre (Siguiente Dosis)', {
            'fields': ('requiere_seguimiento', 'fecha_sugerida_seguimiento', 'notas_seguimiento'),
            'description': 'Si se marca seguimiento, el sistema creará un Recordatorio automático.'
        }),
    )

@admin.register(ServiceFeedback)
class ServiceFeedbackAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'enfermero', 'rating', 'origen', 'fecha_registro')
    list_filter = ('rating', 'enfermero', 'origen')
    search_fields = ('paciente__email', 'enfermero__first_name', 'enfermero__last_name')