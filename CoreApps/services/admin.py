from django.contrib import admin
from .models import ServiceCategory, Service, Medication

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('nombre',)

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    # Mostramos columnas clave para control rápido
    list_display = (
        'nombre', 'categoria', 'precio_base', 'duracion_horas', 
        'es_guardia', 'requiere_retorno', 'activo'
    )
    list_filter = ('categoria', 'es_guardia', 'requiere_retorno', 'activo')
    search_fields = ('nombre',)
    
    # Organización visual para que no se olviden de llenar nada
    fieldsets = (
        ('Información Básica', {
            'fields': ('categoria', 'nombre', 'descripcion', 'activo')
        }),
        ('Configuración de Precios', {
            'fields': ('precio_base', 'precio_insumos', 'incluye_insumos_por_defecto')
        }),
        ('Agenda y Tiempos', {
            'fields': ('duracion_horas', 'es_guardia')
        }),
        ('Lógica de Retorno (Sueros)', {
            'fields': ('requiere_retorno', 'tiempo_espera_retorno'),
            'description': 'Configuración para servicios que necesitan una segunda visita (sacada).'
        }),
    )

@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'frecuencia_legible', 'activo')
    search_fields = ('nombre',)
    list_filter = ('frecuencia_unidad', 'activo')
    
    def frecuencia_legible(self, obj):
        return f"Cada {obj.frecuencia_valor} {obj.get_frecuencia_unidad_display()}"
    frecuencia_legible.short_description = 'Frecuencia Sugerida'