from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from CoreApps.services.models import Service

# --- 1. ESTADOS DE LA CITA ---
class AppointmentStatus(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre

# --- 2. DISPONIBILIDAD (HORARIOS DEL ENFERMERO) ---
class NurseSchedule(models.Model):
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
    # Regla: O es un día recurrente (Lunes) O es una fecha específica (2025-11-20)
    fecha_especifica = models.DateField(null=True, blank=True, help_text="Usar para excepciones.")
    dia_semana = models.IntegerField(choices=DIAS_SEMANA, null=True, blank=True)
    
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    descanso_inicio = models.TimeField(null=True, blank=True, help_text="Inicio del almuerzo")
    descanso_fin = models.TimeField(null=True, blank=True, help_text="Fin del almuerzo")
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.enfermero} - {self.hora_inicio}-{self.hora_fin}"

# --- 3. MODELO DE CITA PRINCIPAL ---
class Appointment(models.Model):
    UBICACION_CHOICES = [
        ('DOMICILIO', 'Domicilio del Paciente'),
        ('OTRA', 'Otra Ubicación (Alternativa)'),
        ('LOCAL', 'En Local / Base'),
    ]
    
    # Relaciones
    paciente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='citas_paciente', limit_choices_to={'rol': 'CLIENTE'})
    enfermero = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='citas_asignadas', limit_choices_to={'rol': 'ENFERMERO'})
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='citas_creadas')
    servicio = models.ForeignKey(Service, on_delete=models.PROTECT)
    estado = models.ForeignKey(AppointmentStatus, on_delete=models.PROTECT)
    
    # Fechas y Tiempos
    fecha = models.DateField()
    hora_inicio_servicio = models.TimeField(_('Hora Cita'))
    hora_fin_servicio = models.TimeField(_('Hora Fin'), blank=True, null=True)
    hora_salida_base = models.TimeField(_('Hora Salida (Buffer)'), blank=True, null=True)
    
    # --- UBICACIÓN FINAL DE LA CITA ---
    tipo_ubicacion = models.CharField(max_length=20, choices=UBICACION_CHOICES, default='DOMICILIO')
    
    # Estos campos guardan la dirección "congelada" para esta cita específica
    direccion_servicio = models.TextField(_('Dirección del Servicio'), blank=True, help_text="Dirección escrita exacta donde irá el enfermero.")
    referencia_servicio = models.TextField(_('Referencia'), blank=True, null=True)
    google_maps_link = models.URLField(_('Link Google Maps'), max_length=500, blank=True, null=True)
    
    # Coordenadas (Opcional, para futuros mapas)
    latitud = models.DecimalField(max_digits=15, decimal_places=10, null=True, blank=True)
    longitud = models.DecimalField(max_digits=15, decimal_places=10, null=True, blank=True)

    # Costos
    cliente_tiene_insumos = models.BooleanField(default=False)
    precio_final = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    notas = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ['-fecha', '-hora_inicio_servicio']

    def __str__(self):
        return f"{self.fecha} {self.hora_inicio_servicio} - {self.paciente}"

    def save(self, *args, **kwargs):
        # 1. Lógica de Ubicación Automática
        if not self.pk: # Solo al crear, para no sobrescribir si editan manualmente luego
            if self.tipo_ubicacion == 'DOMICILIO':
                # Copiar datos del perfil del cliente
                perfil = getattr(self.paciente, 'perfil_cliente', None)
                if perfil:
                    self.direccion_servicio = perfil.direccion
                    self.referencia_servicio = perfil.referencia_ubicacion
                    self.google_maps_link = perfil.google_maps_link
                    self.latitud = perfil.ubicacion_gps_lat
                    self.longitud = perfil.ubicacion_gps_lng
            
            elif self.tipo_ubicacion == 'LOCAL':
                self.direccion_servicio = "Base Central Hola Enfermera"
                self.google_maps_link = "https://maps.google.com/?q=Base_Central" # Poner link real de la empresa
                self.latitud = None
                self.longitud = None

        # 2. Auto-generar Link si hay coordenadas nuevas (Caso "OTRA")
        if self.tipo_ubicacion == 'OTRA' and self.latitud and self.longitud and not self.google_maps_link:
             self.google_maps_link = f"https://www.google.com/maps/search/?api=1&query={self.latitud},{self.longitud}"

        # 3. Cálculo de Tiempos (Tu lógica de Buffer)
        if self.servicio and self.hora_inicio_servicio:
            start_dt = datetime.combine(self.fecha, self.hora_inicio_servicio)
            # Fin del servicio
            self.hora_fin_servicio = (start_dt + timedelta(minutes=self.servicio.duracion_minutos)).time()
            
            # Salida de base (Buffer solo si NO es local)
            buffer = 0
            if self.tipo_ubicacion != 'LOCAL': # Domicilio u Otra
                buffer = self.servicio.tiempo_traslado_minutos
            self.hora_salida_base = (start_dt - timedelta(minutes=buffer)).time()

        # 4. Cálculo de Precio
        if self.servicio:
            costo = self.servicio.precio_base
            if not self.servicio.incluye_insumos_por_defecto and not self.cliente_tiene_insumos:
                costo += self.servicio.precio_insumos
            self.precio_final = costo

        super().save(*args, **kwargs)

    def clean(self):
        # Validación básica de Guardias (Día completo)
        if self.servicio.es_guardia:
            # Aquí iría lógica compleja para asegurar que no haya otras citas ese día
            # Para el MVP, solo validamos que si es guardia, el enfermero esté definido
            if not self.enfermero:
                raise ValidationError("Las guardias requieren asignar un enfermero inmediatamente.")