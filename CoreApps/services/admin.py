from django.contrib import admin
from .models import ServiceCategory, Service

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('nombre',)

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio_base', 'duracion_minutos', 'es_guardia', 'activo')
    list_filter = ('categoria', 'es_guardia', 'permite_domicilio', 'activo')
    search_fields = ('nombre',)
    fieldsets = (
        ('Información Básica', {
            'fields': ('categoria', 'nombre', 'descripcion', 'activo')
        }),
        ('Precios', {
            'fields': ('precio_base', 'precio_insumos', 'incluye_insumos_por_defecto')
        }),
        ('Tiempos y Logística', {
            'fields': (('duracion_minutos', 'tiempo_traslado_minutos'), ('permite_local', 'permite_domicilio'))
        }),
        ('Configuración Especial', {
            'fields': ('es_guardia', 'requiere_retorno', 'tiempo_espera_retorno'),
            'classes': ('collapse',),
        }),
    )