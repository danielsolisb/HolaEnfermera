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
    list_display = ('paciente', 'info_tratamiento', 'fecha_limite_sugerida', 'estado', 'origen')
    list_filter = ('estado', 'origen', 'fecha_limite_sugerida')
    search_fields = ('paciente__email', 'paciente__cedula', 'medicamento_externo')
    date_hierarchy = 'fecha_creacion' # Cambiamos a fecha_creacion porque fecha_limite puede ser null
    
    fieldsets = (
        ('Datos del Paciente', {
            'fields': ('paciente', 'origen', 'estado')
        }),
        ('¿Qué necesita?', {
            'fields': ('servicio_sugerido', 'medicamento_externo', 'notas'),
            'description': 'Si es de la Web, "Servicio" estará vacío y "Medicamento" lleno. Usted debe asignar el Servicio real.'
        }),
        ('Agenda', {
            'fields': ('fecha_limite_sugerida', 'enfermero_sugerido', 'cita_origen')
        }),
    )

    def info_tratamiento(self, obj):
        if obj.servicio_sugerido:
            return obj.servicio_sugerido.nombre
        return obj.medicamento_externo or "Sin especificar"
    info_tratamiento.short_description = 'Tratamiento'