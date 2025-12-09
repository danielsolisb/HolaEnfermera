from django.db import models
from CoreApps.appointments.models import AppointmentReminder

class NotificationLog(models.Model):
    """
    Log de auditoría para envíos de recordatorios automáticos.
    """
    recordatorio = models.ForeignKey(AppointmentReminder, on_delete=models.CASCADE, related_name='logs_notificaciones')
    fecha_intento = models.DateTimeField(auto_now_add=True)
    enviado = models.BooleanField(default=False)
    respuesta_api = models.TextField(blank=True, null=True)
    metodo = models.CharField(max_length=50, default='WHATSAPP')

    def __str__(self):
        estado = "Enviado" if self.enviado else "Fallo"
        return f"{self.fecha_intento.strftime('%Y-%m-%d %H:%M')} - {estado} - {self.recordatorio.paciente}"
