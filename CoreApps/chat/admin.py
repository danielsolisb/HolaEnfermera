from django.contrib import admin
from .models import WhatsAppConversation, WhatsAppMessage

class WhatsAppMessageInline(admin.TabularInline):
    model = WhatsAppMessage
    extra = 0
    readonly_fields = ('fecha',)

@admin.register(WhatsAppConversation)
class WhatsAppConversationAdmin(admin.ModelAdmin):
    list_display = ('telefono', 'get_contacto', 'no_leido', 'fecha_ultimo_mensaje')
    search_fields = ('telefono', 'contacto_crm__nombres', 'contacto_crm__apellidos')
    list_filter = ('no_leido',)
    inlines = [WhatsAppMessageInline]

    def get_contacto(self, obj):
        if obj.contacto_crm:
            return f"{obj.contacto_crm.nombres} {obj.contacto_crm.apellidos}"
        return "Desconocido"
    get_contacto.short_description = 'Contacto CRM'

@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ('conversacion', 'es_entrante', 'fecha', 'estado_envio')
    search_fields = ('conversacion__telefono', 'contenido')
    list_filter = ('es_entrante', 'estado_envio')
