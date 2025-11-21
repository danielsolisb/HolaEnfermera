from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from CoreApps.appointments.models import Appointment

class Payment(models.Model):
    METODOS = [
        ('TRANSFERENCIA', 'Transferencia Bancaria'),
        ('DEPOSITO', 'Depósito Bancario'),
        ('TARJETA', 'Tarjeta de Crédito/Débito (Link)'),
        ('EFECTIVO', 'Efectivo (Cobrado por Enfermero)'),
    ]
    
    ESTADOS = [
        ('PENDIENTE', 'Pendiente de Verificación'),
        ('APROBADO', 'Aprobado / Cobrado'),
        ('RECHAZADO', 'Rechazado / No Acreditado'),
    ]

    # Relación
    cita = models.ForeignKey(
        Appointment, 
        on_delete=models.CASCADE, 
        related_name='pagos',
        help_text="Cita a la que abona este pago."
    )
    
    # Datos Generales
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=20, choices=METODOS, default='TRANSFERENCIA')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    
    # --- DETALLES ESPECÍFICOS DE TRANSFERENCIA ---
    # Estos campos son vitales para conciliación bancaria
    banco_origen = models.CharField(
        _('Banco de Origen'), 
        max_length=100, 
        blank=True, null=True,
        help_text="Banco desde donde envía el cliente (ej: Pichincha, Guayaquil)."
    )
    banco_destino = models.CharField(
        _('Banco de Destino'), 
        max_length=100, 
        blank=True, null=True,
        help_text="Banco de Hola Enfermera donde se recibió el dinero."
    )
    titular_cuenta_origen = models.CharField(
        _('Nombre Titular Cta Origen'), 
        max_length=200, 
        blank=True, null=True,
        help_text="Nombre del dueño de la cuenta desde donde se transfirió (a veces no es el paciente)."
    )
    numero_documento = models.CharField(
        _('N° Documento / Ref.'), 
        max_length=100, 
        blank=True, null=True,
        help_text="Código único de la transferencia o número de comprobante."
    )
    
    # Evidencia
    comprobante_imagen = models.ImageField(
        upload_to='pagos/comprobantes/', 
        blank=True, null=True,
        help_text="Foto/Captura del voucher."
    )
    
    # Auditoría
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        help_text="Usuario que subió el pago."
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_verificacion = models.DateTimeField(blank=True, null=True)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Gestión de Pagos"
        ordering = ['-fecha_registro']

    def __str__(self):
        ref = f"- Ref: {self.numero_documento}" if self.numero_documento else ""
        return f"${self.monto} ({self.get_metodo_pago_display()}) {ref}"