from django.contrib import admin
from .models import Appointment, AppointmentStatus, NurseSchedule

@admin.register(AppointmentStatus)
class AppointmentStatusAdmin(admin.ModelAdmin):
    list_display = ('nombre',)

@admin.register(NurseSchedule)
class NurseScheduleAdmin(admin.ModelAdmin):
    list_display = ('enfermero', 'dia_semana', 'hora_inicio', 'hora_fin')

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        'fecha', 'hora_inicio_servicio', 'paciente', 
        'servicio', 'tipo_ubicacion', 'precio_final', 'estado'
    )
    list_filter = ('estado', 'fecha', 'tipo_ubicacion')
    search_fields = ('paciente__email', 'paciente__cedula')
    readonly_fields = ('hora_fin_servicio', 'hora_salida_base', 'precio_final')

    fieldsets = (
        ('Datos Principales', {
            'fields': ('paciente', 'servicio', 'enfermero', 'estado', 'creado_por')
        }),
        ('Agenda', {
            'fields': ('fecha', 'hora_inicio_servicio', 'hora_fin_servicio', 'hora_salida_base')
        }),
        ('Ubicación del Servicio', {
            'fields': (
                'tipo_ubicacion', 
                'direccion_servicio', 
                'referencia_servicio', 
                'google_maps_link',
                ('latitud', 'longitud')
            ),
            'description': 'Si selecciona DOMICILIO, estos datos se llenarán solos al guardar.'
        }),
        ('Costos y Notas', {
            'fields': ('cliente_tiene_insumos', 'precio_final', 'notas')
        }),
    )