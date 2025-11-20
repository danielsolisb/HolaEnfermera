from django.db import models
from django.utils.translation import gettext_lazy as _

class ServiceCategory(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    icono = models.ImageField(upload_to='servicios/iconos/', blank=True, null=True)

    class Meta:
        verbose_name = "Categoría de Servicio"
        verbose_name_plural = "Categorías de Servicios"

    def __str__(self):
        return self.nombre

class Service(models.Model):
    categoria = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name='servicios')
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    
    # --- PRECIOS ---
    precio_base = models.DecimalField(_('Precio del Servicio'), max_digits=10, decimal_places=2)
    precio_insumos = models.DecimalField(
        _('Costo Adicional Insumos'), 
        max_digits=10, decimal_places=2, 
        default=5.00,
        help_text=_('Se suma si el cliente NO tiene sus propios insumos.')
    )
    incluye_insumos_por_defecto = models.BooleanField(
        default=False, 
        help_text=_('Si es True (ej: Sueroterapia), el precio base ya cubre todo.')
    )

    # --- TIEMPOS Y LOGÍSTICA ---
    duracion_minutos = models.PositiveIntegerField(
        _('Duración Servicio (min)'), 
        help_text=_('Tiempo real ejecutando el servicio con el paciente.')
    )
    tiempo_traslado_minutos = models.PositiveIntegerField(
        _('Tiempo Traslado Default (min)'), 
        default=30,
        help_text=_('Tiempo estimado que el enfermero necesita para llegar (Buffer Previo).')
    )
    
    # --- TIPOS DE SERVICIO ---
    es_guardia = models.BooleanField(
        _('Es Guardia'),
        default=False, 
        help_text=_('Si es True, requiere validación de día completo o turno largo (8h, 12h, 24h).')
    )
    requiere_retorno = models.BooleanField(
        _('Requiere Retorno'),
        default=False,
        help_text=_('Para servicios tipo "Bumerán" (Puesta y retiro de suero).')
    )
    tiempo_espera_retorno = models.PositiveIntegerField(
        _('Tiempo para retiro (horas)'), 
        default=0, 
        blank=True,
        help_text=_('Ej: 6 horas para retirar el suero.')
    )
    
    # --- RESTRICCIONES ---
    permite_local = models.BooleanField(default=True, verbose_name="Disponible en Base/Local")
    permite_domicilio = models.BooleanField(default=True, verbose_name="Disponible a Domicilio")
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"

    def __str__(self):
        tipo = " [GUARDIA]" if self.es_guardia else ""
        return f"{self.nombre} ({self.duracion_minutos} min){tipo}"