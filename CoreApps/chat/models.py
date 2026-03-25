from django.db import models
from CoreApps.crm_marketing.models import CrmContact
#modelo para el crm
class WhatsAppConversation(models.Model):
    telefono = models.CharField(max_length=20, unique=True, verbose_name="Teléfono (WhatsApp)")
    contacto_crm = models.ForeignKey(CrmContact, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversaciones')
    
    no_leido = models.BooleanField(default=True, verbose_name="Mensaje no leído")
    fecha_ultimo_mensaje = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Conversación de WhatsApp"
        verbose_name_plural = "Conversaciones de WhatsApp"
        ordering = ['-fecha_ultimo_mensaje']

    def __str__(self):
        nombre = f" ({self.contacto_crm.nombres} {self.contacto_crm.apellidos})" if self.contacto_crm else ""
        return f"{self.telefono}{nombre}"

#modelo para el chat
class WhatsAppMessage(models.Model):
    conversacion = models.ForeignKey(WhatsAppConversation, on_delete=models.CASCADE, related_name='mensajes')
    
    es_entrante = models.BooleanField(default=True, verbose_name="¿Es mensaje entrante?")
    contenido = models.TextField(verbose_name="Contenido del Mensaje")
    estado_envio = models.CharField(max_length=20, blank=True, null=True, help_text="Ej: Sent, Delivered, Read, Failed (para salientes)")
    
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mensaje de WhatsApp"
        verbose_name_plural = "Mensajes de WhatsApp"
        ordering = ['fecha'] # Orden cronológico para pintar el chat

    def __str__(self):
        tipo = "Entrante" if self.es_entrante else "Saliente"
        return f"{tipo} - {self.fecha.strftime('%d/%m %H:%M')}"

class ChatMensaje(models.Model):
    DIRECCION_CHOICES = [
        ('INBOUND', 'Entrante (Del Cliente)'),
        ('OUTBOUND', 'Saliente (Hacia el Cliente)'),
    ]
    
    ESTADO_CHOICES = [
        ('ENVIADO', 'Enviado'),
        ('ENTREGADO', 'Entregado'),
        ('LEIDO', 'Leído'),
        ('ERROR', 'Error'),
    ]

    MEDIA_TYPE_CHOICES = [
        ('TEXT', 'Texto'),
        ('IMAGE', 'Imagen'),
        ('VIDEO', 'Video'),
        ('AUDIO', 'Audio/Voz'),
        ('DOCUMENT', 'Documento'),
    ]

    contacto = models.ForeignKey('crm_marketing.CrmContact', on_delete=models.CASCADE, related_name='historial_chat')
    direccion = models.CharField(max_length=15, choices=DIRECCION_CHOICES)
    texto = models.TextField(blank=True, null=True)
    
    # Multimedia
    media_url = models.URLField(max_length=1000, blank=True, null=True)
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES, default='TEXT')
    media_key = models.CharField(max_length=200, blank=True, null=True)
    mimetype = models.CharField(max_length=100, blank=True, null=True)
    
    # Metadatos técnicos
    wasender_message_id = models.CharField(max_length=200, blank=True, null=True, unique=True)
    estado_envio = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ENVIADO')
    fecha_mensaje = models.DateTimeField(auto_now_add=True)
    
    # Para saber si un operador ya vio un mensaje "Entrante"
    leido_por_operador = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Mensaje de Chat CRM"
        verbose_name_plural = "Mensajes de Chat CRM"
        ordering = ['fecha_mensaje']

    def __str__(self):
        prefijo = "⬅️" if self.direccion == 'INBOUND' else "➡️"
        return f"{prefijo} {self.contacto.nombres}: {str(self.texto)[:30]}"
