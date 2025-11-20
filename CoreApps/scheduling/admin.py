from django.contrib import admin
from .models import NurseSchedule

@admin.register(NurseSchedule)
class NurseScheduleAdmin(admin.ModelAdmin):
    list_display = ('enfermero', 'tipo_turno', 'hora_inicio', 'hora_fin', 'activo')
    list_filter = ('enfermero', 'activo', 'dia_semana')
    search_fields = ('enfermero__email', 'enfermero__cedula')
    
    def tipo_turno(self, obj):
        return obj.get_dia_semana_display() if obj.dia_semana is not None else obj.fecha_especifica