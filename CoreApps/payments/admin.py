from django.contrib import admin
from .models import Payment
from django.utils.html import format_html
from django.utils import timezone

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'cita_link', 'monto', 'metodo_pago', 'banco_origen',
        'estado', 'fecha_registro', 'ver_comprobante'
    )
    list_filter = ('estado', 'metodo_pago', 'fecha_registro', 'banco_destino')
    search_fields = ('cita__paciente__email', 'numero_documento', 'titular_cuenta_origen')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('cita', 'monto', 'metodo_pago', 'estado')
        }),
        ('Detalles de Transferencia', {
            'fields': ('banco_origen', 'banco_destino', 'titular_cuenta_origen', 'numero_documento'),
            'description': 'Llenar estos datos obligatoriamente si el método es Transferencia o Depósito.',
            'classes': ('collapse',), # Opcional: hace que se pueda ocultar si molesta
        }),
        ('Evidencia y Notas', {
            'fields': ('comprobante_imagen', 'notas')
        }),
        ('Auditoría', {
            'fields': ('registrado_por', 'fecha_registro', 'fecha_verificacion')
        }),
    )
    readonly_fields = ('fecha_registro', 'fecha_verificacion')

    def save_model(self, request, obj, form, change):
        # Automatización: Si cambian a APROBADO, marcamos fecha y quién lo hizo
        if obj.estado == 'APROBADO' and not obj.fecha_verificacion:
            obj.fecha_verificacion = timezone.now()
        # Si no se especificó quién registra, es el usuario actual
        if not obj.registrado_por:
            obj.registrado_por = request.user
            
        super().save_model(request, obj, form, change)

    def cita_link(self, obj):
        return f"Cita #{obj.cita.id} - {obj.cita.paciente}"
    cita_link.short_description = 'Cita'

    def ver_comprobante(self, obj):
        if obj.comprobante_imagen:
            return format_html('<a href="{}" target="_blank" class="button">Ver Imagen</a>', obj.comprobante_imagen.url)
        return "-"
    ver_comprobante.short_description = 'Voucher'