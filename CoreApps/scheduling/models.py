from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class NurseSchedule(models.Model):
    """
    Define los turnos de trabajo de los enfermeros.
    Portal: Exclusivo para gestión de RRHH o Enfermero.
    """
    DIAS_SEMANA = [
        (0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'), (3, 'Jueves'),
        (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo'),
    ]
    
    enfermero = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        limit_choices_to={'rol': 'ENFERMERO'},
        related_name='turnos_trabajo'
    )
    
    # Lógica Híbrida: Recurrente vs Específica
    dia_semana = models.IntegerField(
        choices=DIAS_SEMANA, null=True, blank=True,
        help_text="Para turnos fijos (ej: Todos los Lunes)"
    )
    fecha_especifica = models.DateField(
        null=True, blank=True,
        help_text="Para excepciones o días extra (ej: 2025-12-25)"
    )
    
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    
    # Almuerzo (Bloqueo duro)
    descanso_inicio = models.TimeField(null=True, blank=True)
    descanso_fin = models.TimeField(null=True, blank=True)
    
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Turno de Enfermero"
        verbose_name_plural = "Gestión de Turnos"
        ordering = ['enfermero', 'dia_semana', 'fecha_especifica']

    def __str__(self):
        tipo = f"Día {self.get_dia_semana_display()}" if self.dia_semana is not None else f"Fecha {self.fecha_especifica}"
        return f"{self.enfermero} | {tipo} | {self.hora_inicio}-{self.hora_fin}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.dia_semana is None and self.fecha_especifica is None:
            raise ValidationError("Debe indicar un Día de la semana O una Fecha específica.")
        if self.dia_semana is not None and self.fecha_especifica is not None:
            raise ValidationError("No mezcle días recurrentes con fechas específicas en el mismo registro.")