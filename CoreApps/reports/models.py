from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from CoreApps.appointments.models import Appointment, AppointmentReminder

class ServiceReport(models.Model):
    """
    Reporte final que llena el enfermero al terminar.
    Incluye firma y gatilla la estrategia de re-agendamiento.
    """
    cita = models.OneToOneField(
        Appointment, 
        on_delete=models.CASCADE, 
        related_name='reporte_servicio',
        verbose_name=_('Cita Vinculada')
    )
    
    # --- EVIDENCIA Y CALIDAD ---
    observaciones_tecnicas = models.TextField(_('Observaciones del Procedimiento'), blank=True)
    foto_evidencia = models.ImageField(upload_to='reportes/evidencias/', blank=True, null=True)
    firma_paciente_digital = models.ImageField(
        upload_to='reportes/firmas/', 
        blank=True, null=True,
        help_text=_('Imagen de la firma digital capturada en pantalla')
    )
    
    # --- ESTRATEGIA DE CIERRE (Re-compra) ---
    requiere_seguimiento = models.BooleanField(
        _('¿Requiere Siguiente Dosis?'),
        default=False,
        help_text=_('Si marcas esto, se creará una alerta para agendar la próxima visita.')
    )
    fecha_sugerida_seguimiento = models.DateField(
        _('Fecha Próxima Dosis'), 
        blank=True, null=True
    )
    notas_seguimiento = models.TextField(
        _('Detalle Receta/Tratamiento'), 
        blank=True, 
        help_text=_('Ej: Neurobión cada 24h por 3 días.')
    )
    
    # Auditoría
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Reporte de Servicio"
        verbose_name_plural = "Reportes de Servicios"

    def __str__(self):
        return f"Reporte Cita #{self.cita.id} - {self.cita.paciente}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # --- AUTOMATIZACIÓN: Generar Recordatorio ---
        # Si el enfermero dice que hay seguimiento, creamos el 'Lead' automáticamente.
        if self.requiere_seguimiento and self.fecha_sugerida_seguimiento:
            # Verificamos si ya existe para no duplicar
            existe = AppointmentReminder.objects.filter(cita_origen=self.cita).exists()
            if not existe:
                AppointmentReminder.objects.create(
                    paciente=self.cita.paciente,
                    servicio_sugerido=self.cita.servicio, # Sugerimos el mismo servicio
                    cita_origen=self.cita,
                    enfermero_sugerido=self.cita.enfermero, # El abuelito quiere al mismo enfermero
                    fecha_limite_sugerida=self.fecha_sugerida_seguimiento,
                    notas=self.notas_seguimiento,
                    estado='PENDIENTE'
                )