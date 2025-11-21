from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
import calendar
from CoreApps.services.models import Service, Medication

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
    referencia_servicio = models.TextField(blank=True, null=True)
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
    # ... (ESTADOS, ORIGEN_CHOICES, FKs se mantienen igual) ...
    ESTADOS = [
        ('PENDIENTE', 'Pendiente de Gestión'),
        ('CONTACTADO', 'Cliente Contactado'),
        ('AGENDADO', 'Convertido en Cita'),
        ('CANCELADO', 'Descartado'),
    ]
    ORIGEN_CHOICES = [
        ('SISTEMA', 'Generado por Cierre de Cita'),
        ('WEB', 'Solicitud desde Landing Page'),
    ]

    paciente = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='recordatorios',
        limit_choices_to={'rol': 'CLIENTE'}
    )
    
    servicio_sugerido = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    
    # --- Vínculo con el nuevo modelo de Medicamento ---
    medicamento_catalogo = models.ForeignKey(
        Medication, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        verbose_name="Medicamento (Catálogo)",
        help_text="Si se selecciona, calcula la fecha usando Meses/Años."
    )
    
    medicamento_externo = models.CharField(max_length=200, blank=True, null=True)
    
    cita_origen = models.ForeignKey('Appointment', on_delete=models.SET_NULL, null=True, blank=True, related_name='recordatorios_generados')
    enfermero_sugerido = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='recordatorios_asignados')

    fecha_limite_sugerida = models.DateField(null=True, blank=True)
    
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES, default='SISTEMA')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    notas = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Recordatorio / Lead"
        verbose_name_plural = "Recordatorios y Leads"
        ordering = ['fecha_limite_sugerida', '-fecha_creacion']

    def __str__(self):
        tema = self.medicamento_catalogo.nombre if self.medicamento_catalogo else (self.medicamento_externo or "General")
        fecha = self.fecha_limite_sugerida or "Sin fecha"
        return f"{self.paciente} - {tema} ({fecha})"

    def _add_months(self, source_date, months):
        """Función auxiliar para sumar meses correctamente (evita errores de calendario)"""
        month = source_date.month - 1 + months
        year = source_date.year + month // 12
        month = month % 12 + 1
        day = min(source_date.day, calendar.monthrange(year, month)[1])
        return source_date.replace(year=year, month=month, day=day)

    def save(self, *args, **kwargs):
        # AUTOMATIZACIÓN DE FECHA POR TIPO (DÍAS, MESES, AÑOS)
        if not self.fecha_limite_sugerida and self.medicamento_catalogo:
            valor = self.medicamento_catalogo.frecuencia_valor
            unidad = self.medicamento_catalogo.frecuencia_unidad
            
            ahora = timezone.now().date()
            
            if unidad == 'DIAS':
                self.fecha_limite_sugerida = ahora + timedelta(days=valor)
            elif unidad == 'MESES':
                self.fecha_limite_sugerida = self._add_months(ahora, valor)
            elif unidad == 'ANIOS':
                self.fecha_limite_sugerida = self._add_months(ahora, valor * 12)
            
        super().save(*args, **kwargs)