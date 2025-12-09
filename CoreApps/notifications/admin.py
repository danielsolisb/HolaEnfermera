from django.contrib import admin
from .models import NotificationLog

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('fecha_intento', 'recordatorio_info', 'enviado', 'metodo', 'respuesta_short')
    list_filter = ('enviado', 'metodo', 'fecha_intento')
    search_fields = ('recordatorio__paciente__email', 'recordatorio__paciente__cedula', 'recordatorio__paciente__first_name')
    readonly_fields = ('fecha_intento', 'recordatorio', 'enviado', 'respuesta_api', 'metodo')
    ordering = ('-fecha_intento',)

    def recordatorio_info(self, obj):
        return str(obj.recordatorio)
    recordatorio_info.short_description = 'Recordatorio Asignado'

    def respuesta_short(self, obj):
        return (obj.respuesta_api[:50] + '...') if obj.respuesta_api and len(obj.respuesta_api) > 50 else obj.respuesta_api
    respuesta_short.short_description = 'Respuesta API'
