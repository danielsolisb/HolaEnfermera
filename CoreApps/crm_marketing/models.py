from django.db import models
from django.conf import settings
from CoreApps.main.models import Ciudad

class Farmacia(models.Model):
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código de Farmacia")
    nombre = models.CharField(max_length=150, verbose_name="Nombre de Farmacia")
    ciudad = models.ForeignKey(Ciudad, on_delete=models.PROTECT, related_name='farmacias')

    class Meta:
        verbose_name = "Farmacia"
        verbose_name_plural = "Farmacias"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"

class Etiqueta(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=20, default="#3366cc", help_text="Color para el badge en el dashboard")

    class Meta:
        verbose_name = "Etiqueta CRM"
        verbose_name_plural = "Etiquetas CRM"

    def __str__(self):
        return self.nombre

class ProductoCRM(models.Model):
    nombre = models.CharField(max_length=200, unique=True, verbose_name="Nombre Comercial")
    
    class Meta:
        verbose_name = "Producto (Lead Farmacia)"
        verbose_name_plural = "Productos (Leads Farmacias)"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

class CrmContact(models.Model):
    # Identidad
    nombres = models.CharField(max_length=150, verbose_name="Nombres")
    apellidos = models.CharField(max_length=150, verbose_name="Apellidos")
    cedula = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="Cédula/RUC")
    fecha_nacimiento = models.DateField(blank=True, null=True, verbose_name="Fecha de Nacimiento")
    es_edad_estimada = models.BooleanField(default=False, help_text="True si no se dio fecha exacta y se calculó el año base a su edad proporcionada.")

    
    # Contacto
    telefono = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="Teléfono (WhatsApp)")
    whatsapp_jid = models.CharField(max_length=150, blank=True, null=True, verbose_name="WhatsApp JID")
    whatsapp_lid = models.CharField(max_length=150, blank=True, null=True, verbose_name="WhatsApp LID (Linked Device ID)")
    email = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    
    # Ubicación (Relacionado a main.Ciudad)
    ciudad = models.ForeignKey(Ciudad, on_delete=models.PROTECT, related_name='contactos_crm', null=True, blank=True)
    zona_barrio = models.CharField(max_length=200, blank=True, null=True, verbose_name="Zona / Barrio")
    
    # Relaciones CRM
    farmacia_origen = models.ForeignKey(Farmacia, on_delete=models.SET_NULL, null=True, blank=True, related_name='contactos')
    etiquetas = models.ManyToManyField(Etiqueta, blank=True, related_name='contactos')
    medicamentos_comprados = models.ManyToManyField(ProductoCRM, blank=True, related_name='compradores')

    # Nuevo: Pipeline / Embudo de Ventas
    ETAPAS_CHOICES = [
        ('LEAD', 'Lead Entrante'),
        ('CONTACTADO', 'Primer Contacto'),
        ('NEGOCIACION', 'En Negociación'),
        ('GANADO', 'Venta Cerrada (Éxito)'),
        ('PERDIDO', 'Venta Perdida'),
        ('DESCARTADO', 'Descartado / Competencia'),
    ]
    etapa_comercial = models.CharField(max_length=20, choices=ETAPAS_CHOICES, default='LEAD', verbose_name="Etapa del Pipeline")
    fecha_ultima_actividad = models.DateTimeField(null=True, blank=True, verbose_name="Fecha última actividad")

    
    # Transformación a App principal
    usuario_vinculado = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='perfil_crm',
        help_text="Usuario real del ERP/App si fue convertido."
    )

    es_organico = models.BooleanField(default=False, verbose_name="¿Es Orgánico? (WhatsApp)")
    es_proveedor = models.BooleanField(default=False, verbose_name="Es Proveedor (Oculto de Pipeline)")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # Trazabilidad de Respuesta (KPIs)
    fecha_creacion_lead = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Creación del Lead")
    fecha_primer_contacto = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Primer Contacto")
    tiempo_respuesta_inicial = models.DurationField(null=True, blank=True, verbose_name="Tiempo de Respuesta Inicial")

    @property
    def is_hidden_number(self):
        """Verifica si el número almacenado es en realidad un LID de WhatsApp."""
        if self.whatsapp_jid and '@lid' in self.whatsapp_jid:
            return True
        if self.telefono and len(self.telefono) > 13 and (self.telefono.startswith('+1') or self.telefono.startswith('+2') or self.telefono.startswith('+6')):
            return True
        return False

    @property
    def display_phone(self):
        """Retorna el teléfono o 'Número Oculto' si es un LID."""
        if self.is_hidden_number:
            return "Número Oculto"
        return self.telefono

    class Meta:
        verbose_name = "Contacto CRM"
        verbose_name_plural = "Contactos CRM"
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"{self.nombres} {self.apellidos} ({self.telefono})"

    def save(self, *args, **kwargs):
        # En MySQL, unique=True permite múltiples NULLs pero no múltiples cadenas vacías.
        # Convertimos cadenas vacías a None para permitir contactos sin teléfono/cédula.
        if self.telefono == "":
            self.telefono = None
        if self.cedula == "":
            self.cedula = None
        super().save(*args, **kwargs)

    def get_sangre_fria_info(self):
        """Calcula si el lead está en 'sangre fría' (excedió tiempo de respuesta)"""
        if self.etapa_comercial != 'LEAD' or not self.fecha_creacion_lead or self.fecha_primer_contacto:
            return {'exceeded': False, 'minutes': 0}
        
        from django.utils import timezone
        from .models import CrmConfig
        config = CrmConfig.get_solo()
        
        diff = timezone.now() - self.fecha_creacion_lead
        minutes = int(diff.total_seconds() / 60)
        
        return {
            'exceeded': minutes >= config.tiempo_alerta_leads,
            'minutes': minutes,
            'limit': config.tiempo_alerta_leads
        }

    def get_campanas_nombres(self):
        """Devuelve una lista de nombres de campañas en las que ha participado"""
        return list(self.mensajes_campana.all().values_list('campana__nombre', flat=True).distinct())

class CampanaDifusion(models.Model):
    ESTADOS = [
        ('BORRADOR', 'Borrador'),
        ('PROGRAMADA', 'Programada'),
        ('ENVIANDO', 'Enviando...'),
        ('COMPLETADA', 'Completada'),
        ('ERROR', 'Error')
    ]

    nombre = models.CharField(max_length=200, verbose_name="Nombre de la Campaña")
    mensaje_plantilla = models.TextField(verbose_name="Mensaje de WhatsApp")
    
    # Filtros de Audiencia
    ciudades_objetivo = models.ManyToManyField(Ciudad, blank=True, verbose_name="Filtro por Ciudad")
    etiquetas_objetivo = models.ManyToManyField(Etiqueta, blank=True, verbose_name="Filtro por Etiquetas")
    farmacias_objetivo = models.ManyToManyField(Farmacia, blank=True, verbose_name="Filtro por Farmacias")
    medicamentos_objetivo = models.ManyToManyField(ProductoCRM, blank=True, verbose_name="Filtro por Productos/Medicamentos")
    
    edad_minima = models.PositiveIntegerField(blank=True, null=True, verbose_name="Edad Mínima (Filtro)")
    edad_maxima = models.PositiveIntegerField(blank=True, null=True, verbose_name="Edad Máxima (Filtro)")
    
    estado = models.CharField(max_length=20, choices=ESTADOS, default='BORRADOR')
    fecha_programada = models.DateTimeField(blank=True, null=True, verbose_name="Enviar a partir de")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Campaña de Difusión"
        verbose_name_plural = "Campañas de Difusión"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return self.nombre

    def get_audiencia(self):
        """Calcula el número de personas que coinciden con los filtros. Lógica AND."""
        from django.db.models import Q
        import datetime
        
        # Iniciar con todos los contactos
        qs = CrmContact.objects.all()

        if self.ciudades_objetivo.exists():
            qs = qs.filter(ciudad__in=self.ciudades_objetivo.all())
            
        if self.farmacias_objetivo.exists():
            qs = qs.filter(farmacia_origen__in=self.farmacias_objetivo.all())
            
        if self.etiquetas_objetivo.exists():
            for etiqueta in self.etiquetas_objetivo.all():
                qs = qs.filter(etiquetas=etiqueta)
                
        if self.medicamentos_objetivo.exists():
            for med in self.medicamentos_objetivo.all():
                qs = qs.filter(medicamentos_comprados=med)

        # Filtro de Edad
        if self.edad_minima is not None or self.edad_maxima is not None:
            hoy = datetime.date.today()
            
            # Si piden edad MINIMA = 18, significa que deben haber nacido HACE MÁS de 18 años.
            # O sea, fecha_nacimiento <= HOY - 18 años
            if self.edad_minima is not None:
                # Calculo de forma simplificada restando años
                fecha_tope_min = datetime.date(hoy.year - self.edad_minima, hoy.month, hoy.day)
                qs = qs.filter(fecha_nacimiento__lte=fecha_tope_min)
                
            # Si piden edad MAXIMA = 65, deben haber nacido HACE MENOS de 65 años.
            # O sea, fecha_nacimiento >= HOY - 65 años
            if self.edad_maxima is not None:
                fecha_tope_max = datetime.date(hoy.year - self.edad_maxima, hoy.month, hoy.day)
                qs = qs.filter(fecha_nacimiento__gte=fecha_tope_max)

        return qs.distinct()


class DiffusionLog(models.Model):
    campana = models.ForeignKey(CampanaDifusion, on_delete=models.CASCADE, related_name='logs')
    contacto = models.ForeignKey(CrmContact, on_delete=models.CASCADE, related_name='logs_difusion')
    
    enviado_con_exito = models.BooleanField(default=False)
    mensaje_error = models.TextField(blank=True, null=True)
    fecha_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Log de Difusión"
        verbose_name_plural = "Logs de Difusión"
        ordering = ['-fecha_envio']
        # Evita que se envíe dos veces a la misma persona en la misma campaña
        unique_together = ('campana', 'contacto')

    def __str__(self):
        estado = "Éxito" if self.enviado_con_exito else "Error"
        return f"{self.campana.nombre} -> {self.contacto.telefono} ({estado})"


class MensajeCampana(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente de Envío'),
        ('ENVIADO', 'Enviado (API)'),
        ('ENTREGADO', 'Entregado (Check Gris)'),
        ('LEIDO', 'Leído (Check Azul)'),
        ('ERROR', 'Error de Envío')
    ]
    campana = models.ForeignKey(CampanaDifusion, on_delete=models.CASCADE, related_name='mensajes_cola')
    contacto = models.ForeignKey(CrmContact, on_delete=models.CASCADE, related_name='mensajes_campana')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    
    # Rastrear con Webhooks
    wasender_message_id = models.CharField(max_length=150, blank=True, null=True, verbose_name="ID de Mensaje en WASender")
    error_log = models.TextField(blank=True, null=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mensaje de Campaña"
        verbose_name_plural = "Mensajes de Campaña"
        unique_together = ('campana', 'contacto') # Evitar duplicados de la misma campaña
        
    def __str__(self):
        return f"MSG: {self.campana.nombre} -> {self.contacto.telefono} [{self.estado}]"


class CrmConfig(models.Model):
    """Configuración global del CRM (Single Row)"""
    tiempo_alerta_leads = models.PositiveIntegerField(default=30, help_text="Tiempo en minutos para resaltar leads sin atender")
    respuestas_rapidas = models.JSONField(default=list, help_text="Lista de objetos { 'label': '...', 'text': '...' }")
    
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración CRM"
        verbose_name_plural = "Configuraciones CRM"

    def __str__(self):
        return "Configuración Global del CRM"

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(id=1)
        return obj

class CrmMediaTemplate(models.Model):
    """Plantillas de archivos multimedia (Cuentas bancarias, promociones, etc.)"""
    MEDIA_TYPES = [
        ('IMAGE', 'Imagen'),
        ('VIDEO', 'Video'),
        ('DOCUMENT', 'Documento/PDF'),
    ]
    nombre = models.CharField(max_length=100, verbose_name="Nombre de la Plantilla (Ej: Cuenta Banco)")
    archivo = models.FileField(upload_to='crm/templates/', verbose_name="Archivo Multimedia")
    tipo = models.CharField(max_length=20, choices=MEDIA_TYPES, default='IMAGE')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Plantilla Multimedia"
        verbose_name_plural = "Plantillas Multimedia"
        ordering = ['-fecha_creacion']
        
    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"
