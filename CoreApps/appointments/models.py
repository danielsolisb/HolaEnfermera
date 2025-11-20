from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
from CoreApps.services.models import Service

class AppointmentStatus(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)
    def __str__(self): return self.nombre

class Appointment(models.Model):
    UBICACION_CHOICES = [('DOMICILIO', 'A Domicilio'), ('LOCAL', 'En Local / Base'), ('OTRA', 'Otra Ubicación')]

    # Actores
    paciente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='citas_paciente', limit_choices_to={'rol': 'CLIENTE'})
    enfermero = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='citas_asignadas', limit_choices_to={'rol': 'ENFERMERO'})
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='citas_creadas')
    
    servicio = models.ForeignKey(Service, on_delete=models.PROTECT)
    estado = models.ForeignKey(AppointmentStatus, on_delete=models.PROTECT)
    
    # Agenda
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField(blank=True, null=True, editable=False)
    
    # Ubicación
    tipo_ubicacion = models.CharField(max_length=20, choices=UBICACION_CHOICES, default='DOMICILIO')
    direccion_servicio = models.TextField(blank=True)
    google_maps_link = models.URLField(max_length=500, blank=True, null=True)
    latitud = models.DecimalField(max_digits=15, decimal_places=10, null=True, blank=True)
    longitud = models.DecimalField(max_digits=15, decimal_places=10, null=True, blank=True)

    # Costos
    cliente_tiene_insumos = models.BooleanField(default=False)
    precio_final = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    notas = models.TextField(blank=True)
    
    # Control
    es_reagendada = models.BooleanField(default=False, help_text="Si esta cita viene de un recordatorio/seguimiento.")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ['-fecha', '-hora_inicio']

    def __str__(self):
        return f"{self.fecha} {self.hora_inicio} - {self.paciente} ({self.servicio.nombre})"

    def save(self, *args, **kwargs):
        # Cálculo de fin de cita (Estándar 1 hora o según servicio)
        if self.servicio and self.hora_inicio:
            start_dt = datetime.combine(self.fecha, self.hora_inicio)
            end_dt = start_dt + timedelta(hours=self.servicio.duracion_horas)
            self.hora_fin = end_dt.time()

        # Lógica de Ubicación (Copia perfil)
        if not self.pk and self.tipo_ubicacion == 'DOMICILIO':
             perfil = getattr(self.paciente, 'perfil_cliente', None)
             if perfil:
                 self.direccion_servicio = perfil.direccion
                 self.google_maps_link = perfil.google_maps_link
                 self.latitud = perfil.ubicacion_gps_lat
                 self.longitud = perfil.ubicacion_gps_lng

        # Generar Link si hay coordenadas nuevas
        if self.latitud and self.longitud and not self.google_maps_link:
             self.google_maps_link = f"http://googleusercontent.com/maps.google.com/maps?q={self.latitud},{self.longitud}"

        # Precio
        if self.servicio:
            costo = self.servicio.precio_base
            if not self.servicio.incluye_insumos_por_defecto and not self.cliente_tiene_insumos:
                costo += self.servicio.precio_insumos
            self.precio_final = costo

        super().save(*args, **kwargs)


class AppointmentReminder(models.Model):
    """
    El 'Post-it' inteligente. Se crea cuando un enfermero reporta 
    que el paciente necesita una siguiente dosis.
    """
    ESTADOS = [
        ('PENDIENTE', 'Pendiente de Gestión'),
        ('CONTACTADO', 'Cliente Contactado'),
        ('AGENDADO', 'Convertido en Cita'),
        ('CANCELADO', 'Descartado'),
    ]

    paciente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recordatorios')
    servicio_sugerido = models.ForeignKey(Service, on_delete=models.CASCADE, help_text="El servicio que toca (ej: Misma inyección)")
    cita_origen = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, related_name='recordatorios_generados')
    enfermero_sugerido = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='recordatorios_asignados')
    
    fecha_limite_sugerida = models.DateField(help_text="Fecha ideal para la siguiente dosis")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    notas = models.TextField(blank=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Recordatorio de Dosis"
        verbose_name_plural = "Recordatorios de Dosis"
        ordering = ['fecha_limite_sugerida']

    def __str__(self):
        return f"Recordar: {self.paciente} para {self.fecha_limite_sugerida}"