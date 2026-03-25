from django.contrib import admin
from .models import Farmacia, Etiqueta, CrmContact, CampanaDifusion, DiffusionLog, ProductoCRM, CrmConfig, MensajeCampana, CrmMediaTemplate


@admin.register(CrmConfig)
class CrmConfigAdmin(admin.ModelAdmin):
    list_display = ('id', 'tiempo_alerta_leads', 'fecha_actualizacion')

@admin.register(MensajeCampana)
class MensajeCampanaAdmin(admin.ModelAdmin):
    list_display = ('campana', 'contacto', 'estado', 'fecha_actualizacion')
    list_filter = ('estado', 'campana')


@admin.register(Farmacia)
class FarmaciaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'ciudad')
    search_fields = ('codigo', 'nombre')
    list_filter = ('ciudad',)

@admin.register(Etiqueta)
class EtiquetaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'color')
    search_fields = ('nombre',)

@admin.register(ProductoCRM)
class ProductoCRMAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(CrmContact)
class CrmContactAdmin(admin.ModelAdmin):
    list_display = ('nombres', 'apellidos', 'telefono', 'ciudad', 'farmacia_origen', 'fecha_registro')
    search_fields = ('nombres', 'apellidos', 'telefono', 'cedula', 'email')
    list_filter = ('ciudad', 'farmacia_origen', 'etiquetas', 'es_edad_estimada')
    filter_horizontal = ('etiquetas', 'medicamentos_comprados')


@admin.register(CampanaDifusion)
class CampanaDifusionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'estado', 'fecha_programada', 'fecha_creacion')
    search_fields = ('nombre', 'mensaje_plantilla')
    list_filter = ('estado', 'ciudades_objetivo', 'farmacias_objetivo')
    filter_horizontal = ('ciudades_objetivo', 'etiquetas_objetivo', 'farmacias_objetivo', 'medicamentos_objetivo')
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'mensaje_plantilla', 'estado', 'fecha_programada')
        }),
        ('Audiencia - Geografía y General', {
            'fields': ('ciudades_objetivo', 'etiquetas_objetivo', 'farmacias_objetivo')
        }),
        ('Audiencia - Segmentación Avanzada', {
            'fields': ('medicamentos_objetivo', 'edad_minima', 'edad_maxima')
        }),
    )

@admin.register(DiffusionLog)
class DiffusionLogAdmin(admin.ModelAdmin):
    list_display = ('campana', 'contacto', 'enviado_con_exito', 'fecha_envio')
    search_fields = ('campana__nombre', 'contacto__nombres', 'contacto__apellidos', 'contacto__telefono')
    list_filter = ('enviado_con_exito', 'campana')

@admin.register(CrmMediaTemplate)
class CrmMediaTemplateAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'archivo', 'fecha_creacion')
    list_filter = ('tipo',)
    search_fields = ('nombre',)
