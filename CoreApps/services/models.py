from django.db import models
from django.utils.translation import gettext_lazy as _

class ServiceCategory(models.Model):
    nombre = models.CharField(max_length=100)
    icono = models.ImageField(upload_to='servicios/iconos/', blank=True, null=True)
    
    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self): 
        return self.nombre

class Service(models.Model):
    categoria = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name='servicios')
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    
    # --- PRECIOS (Vital para facturación) ---
    precio_base = models.DecimalField(_('Precio del Servicio'), max_digits=10, decimal_places=2)
    precio_insumos = models.DecimalField(
        _('Costo Insumos Extra'), 
        max_digits=10, decimal_places=2, 
        default=5.00,
        help_text=_('Se suma automáticamente si el cliente NO tiene sus propios insumos.')
    )
    incluye_insumos_por_defecto = models.BooleanField(
        _('Insumos incluidos'),
        default=False, 
        help_text=_('Si marcas esto (ej: Sueroterapia), el precio base ya es el final.')
    )

    # --- TIEMPOS Y LOGÍSTICA ---
    duracion_horas = models.PositiveIntegerField(
        _('Duración (Horas)'), 
        default=1,
        help_text=_('Tiempo que se bloquea en la agenda. Estándar: 1 hora. Guardias: 8, 12, 24.')
    )
    
    # --- TIPOS ESPECIALES ---
    es_guardia = models.BooleanField(
        _('Es Guardia'),
        default=False, 
        help_text=_('Si es True, requiere validación especial (bloqueo de jornada completa).')
    )
    
    # Lógica "Bumerán" (Sueros Puesta y Sacada)
    requiere_retorno = models.BooleanField(
        _('Requiere Retorno'),
        default=False,
        help_text=_('Si es True, el sistema deberá agendar una segunda cita para el retiro (ej: sacar el suero).')
    )
    tiempo_espera_retorno = models.PositiveIntegerField(
        _('Horas para retiro'), 
        default=0, 
        blank=True,
        help_text=_('Ej: Si el suero dura 6 horas, poner 6. El sistema sugerirá la cita de retiro 6h después.')
    )
    
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"

    def __str__(self):
        return f"{self.nombre} (${self.precio_base})"