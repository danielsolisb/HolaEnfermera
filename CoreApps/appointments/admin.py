from django.contrib import admin
from .models import Appointment, AppointmentStatus, AppointmentReminder

@admin.register(AppointmentStatus)
class AppointmentStatusAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        'fecha', 'hora_inicio', 'hora_fin', 
        'paciente_nombre', 'servicio', 'enfermero', 
        'estado', 'precio_final'
    )
    list_filter = ('estado', 'fecha', 'enfermero', 'servicio', 'tipo_ubicacion')
    search_fields = ('paciente__first_name', 'paciente__last_name', 'paciente__email', 'paciente__cedula')
    readonly_fields = ('hora_fin', 'precio_final')
    
    fieldsets = (
        ('Datos de la Reserva', {
            'fields': ('paciente', 'servicio', 'enfermero', 'estado', 'creado_por')
        }),
        ('Agenda', {
            'fields': ('fecha', 'hora_inicio', 'hora_fin')
        }),
        ('Ubicación del Servicio', {
            'fields': (
                'tipo_ubicacion', 
                'direccion_servicio', 
                'referencia_servicio',
                'google_maps_link',
                ('latitud', 'longitud')
            ),
            'description': 'Si selecciona DOMICILIO, estos datos se copiarán del paciente al guardar.'
        }),
        ('Facturación y Seguimiento', {
            'fields': ('cliente_tiene_insumos', 'precio_final', 'es_reagendada')
        }),
        ('Notas', {
            'fields': ('notas',)
        })
    )

    def paciente_nombre(self, obj):
        return f"{obj.paciente.first_name} {obj.paciente.last_name}"
    paciente_nombre.short_description = 'Paciente'

@admin.register(AppointmentReminder)
class AppointmentReminderAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'servicio_sugerido', 'fecha_limite_sugerida', 'estado', 'enfermero_sugerido')
    list_filter = ('estado', 'fecha_limite_sugerida', 'servicio_sugerido')
    search_fields = ('paciente__email', 'paciente__cedula')
    date_hierarchy = 'fecha_limite_sugerida'