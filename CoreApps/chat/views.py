from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import WhatsAppConversation, WhatsAppMessage

class SupervisorChatMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Permite acceso a personal de marketing y ventas (staff) al inbox"""
    def test_func(self):
        return self.request.user.is_staff

import uuid
import datetime

class InboxView(SupervisorChatMixin, TemplateView):
    template_name = 'chat/inbox.html'

    def get_context_data(self, **kwargs):
        # --- LIMPIEZA AUTOMÁTICA DE REGISTROS CORRUPTOS ('' -> None) ---
        from .models import ChatMensaje
        ChatMensaje.objects.filter(wasender_message_id='').update(wasender_message_id=None)
        # -------------------------------------------------------------

        context = super().get_context_data(**kwargs)
        # Obtenemos contactos que tengan historial de chat, ordenados por el último mensaje
        from django.db.models import Max
        from CoreApps.crm_marketing.models import CrmContact
        
        contactos_con_chat = CrmContact.objects.filter(historial_chat__isnull=False).annotate(
            ultimo_msg_fecha=Max('historial_chat__fecha_mensaje')
        ).order_by('-ultimo_msg_fecha')
        
        context['conversaciones'] = contactos_con_chat
        
        # Si viene un contact_id por URL, lo pasamos al contexto para que el JS lo abra
        context['auto_open_contact_id'] = self.request.GET.get('contact_id')
        
        return context

import json
import logging
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from CoreApps.crm_marketing.models import MensajeCampana, CrmContact
from .models import WhatsAppConversation, WhatsAppMessage, ChatMensaje

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class WasenderWebhookView(View):
    """
    Recibe los eventos desde WASenderAPI (ej. message.sent, message.read)
    Documentación oficial: https://wasenderapi.com/api-docs/webhooks/webhook-setup
    """
    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body)
            event = payload.get('event')
            
            # WASender API Eventos comunes
            # 'message.sent' o 'messages.update' (para lecturas)
            if event in ['message.sent', 'messages.update', 'message.read', 'message.ack']:
                data = payload.get('data', {})
                
                if isinstance(data, list):
                    updates = data
                else:
                    updates = [data]
                    
                for upd in updates:
                    # Dependiendo el evento la estructura varía un poco
                    key = upd.get('key', {})
                    wasender_id = key.get('id')
                    
                    if wasender_id:
                        # Buscamos si este mensaje pertenece a una campaña
                        mensajes_campana = MensajeCampana.objects.filter(wasender_message_id=wasender_id)
                        if mensajes_campana.exists():
                            for msg in mensajes_campana:
                                # Extraer el status si viene en events tipo update
                                status = upd.get('update', {}).get('status', '').upper()
                                
                                if status in ['READ', 'SEEN'] or 'read' in str(event):
                                    msg.estado = 'LEIDO'
                                    msg.save(update_fields=['estado'])
                                    
            # Evento de Nuevos Mensajes (Entrantes o Salientes detectados por WhatsApp)
            elif event == 'messages.upsert':
                data = payload.get('data', {})
                messages_list = data.get('messages', [])
                for msg in messages_list:
                    key = msg.get('key', {})
                    from_me = key.get('fromMe', False)
                    remote_jid = key.get('remoteJid', '')
                    
                    # Evitamos procesar mensajes de grupos
                    if '@g.us' in remote_jid:
                        continue
                        
                    # Extraer texto del payload (varía según texto simple o texto extendido)
                    message_content = msg.get('message', {})
                    text_content = message_content.get('conversation') or message_content.get('extendedTextMessage', {}).get('text') or "[Media/Otro formato no soportado]"
                    
                    wasender_id = key.get('id', '')
                    
                    # Formatear teléfono sacando el @s.whatsapp.net
                    telefono_puro = remote_jid.split('@')[0]
                    # Aseguramos el "+"
                    if not telefono_puro.startswith('+'):
                        telefono_puro = f"+{telefono_puro}"
                        
                    # 1. Buscamos el Contacto CRM (Atribución Inteligente por teléfono compartido)
                    contactos_potenciales = CrmContact.objects.filter(telefono=telefono_puro)
                    contacto = None
                    
                    if contactos_potenciales.count() > 1:
                        # Prioridad 1: El que tenga el mensaje de salida más reciente (interacción activa)
                        contacto = contactos_potenciales.annotate(
                            u_fecha=Max('historial_chat__fecha_mensaje')
                        ).order_by('-u_fecha').first()
                        
                        # Si no hay histórico, priorizamos el que sea más reciente por creación
                        if not contacto:
                            contacto = contactos_potenciales.order_by('-id').first()
                    else:
                        contacto = contactos_potenciales.first()

                    if not contacto:
                        contacto = CrmContact.objects.create(
                            telefono=telefono_puro,
                            nombres='Desconocido', 
                            apellidos='(Lead Entrante)',
                            es_edad_estimada=False
                        )
                    
                    # 2. Guardamos el mensaje histórico
                    if wasender_id:
                        if not ChatMensaje.objects.filter(wasender_message_id=wasender_id).exists():
                            ChatMensaje.objects.create(
                                contacto=contacto,
                                direccion='OUTBOUND' if from_me else 'INBOUND',
                                texto=text_content,
                                wasender_message_id=wasender_id,
                                estado_envio='ENTREGADO'
                            )
                    else:
                        # Si por alguna razón no hay ID de WASender, generamos uno único local
                        ChatMensaje.objects.create(
                            contacto=contacto,
                            direccion='OUTBOUND' if from_me else 'INBOUND',
                            texto=text_content,
                            wasender_message_id=f"inbound_loc_{uuid.uuid4().hex[:12]}",
                            estado_envio='ENTREGADO'
                        )
                        
            return JsonResponse({'received': True}, status=200)
        except Exception as e:
            logger.error(f"Error procesando webhook de WASender: {e}")
            return JsonResponse({'error': str(e)}, status=400)


# ==========================================
# ENDPOINTS AJAX PARA EL FRONTEND DEL INBOX
# ==========================================
from django.db.models import Max
from CoreApps.notifications.services import WASenderService

class ChatListAPIView(SupervisorChatMixin, View):
    """Devuelve la lista de contactos ordenados por el último mensaje recibido/enviado"""
    def get(self, request, *args, **kwargs):
        force_contact_id = request.GET.get('force_contact_id')
        
        # Obtenemos contactos que tengan historial de chat
        from django.db.models import Q, Max
        qs = CrmContact.objects.filter(
            Q(historial_chat__isnull=False) | Q(id=force_contact_id) if force_contact_id else Q(historial_chat__isnull=False)
        ).distinct()
        
        contactos = qs.annotate(
            ultimo_msg_fecha=Max('historial_chat__fecha_mensaje')
        ).order_by('-ultimo_msg_fecha')
        
        data = []
        for c in contactos:
            ultimo_mensaje = c.historial_chat.order_by('-fecha_mensaje').first()
            data.append({
                'id': c.id,
                'nombre': f"{c.nombres} {c.apellidos}",
                'telefono': c.telefono,
                'ultimo_mensaje': ultimo_mensaje.texto if ultimo_mensaje else '',
                'fecha_ultimo': ultimo_mensaje.fecha_mensaje.strftime('%d/%m %H:%M') if ultimo_mensaje else '',
                'direccion_ultimo': ultimo_mensaje.direccion if ultimo_mensaje else '',
                'no_leido': not ultimo_mensaje.leido_por_operador if ultimo_mensaje and ultimo_mensaje.direccion == 'INBOUND' else False
            })
        return JsonResponse({'chats': data})

class ChatHistoryAPIView(SupervisorChatMixin, View):
    """Devuelve el historial de un chat específico"""
    def get(self, request, contacto_id, *args, **kwargs):
        contacto = CrmContact.objects.get(id=contacto_id)
        mensajes = ChatMensaje.objects.filter(contacto=contacto).order_by('fecha_mensaje')
        
        # Marcar como leídos por el operador
        mensajes.filter(direccion='INBOUND', leido_por_operador=False).update(leido_por_operador=True)
        
        data = []
        for m in mensajes:
            data.append({
                'id': m.id,
                'direccion': m.direccion,
                'texto': m.texto,
                'fecha': m.fecha_mensaje.strftime('%H:%M - %d/%m/%y'),
                'estado': m.estado_envio
            })
        return JsonResponse({
            'contacto': {
                'id': contacto.id,
                'nombre': f"{contacto.nombres} {contacto.apellidos}",
                'telefono': contacto.telefono
            },
            'mensajes': data
        })

@method_decorator(csrf_exempt, name='dispatch')
class ChatSendAPIView(SupervisorChatMixin, View):
    """Endpoint para enviar un mensaje manualmente desde el Inbox"""
    def post(self, request, contacto_id, *args, **kwargs):
        try:
            contacto = CrmContact.objects.get(id=contacto_id)
            payload = json.loads(request.body)
            texto = payload.get('texto', '').strip()
            
            if not texto:
                return JsonResponse({'error': 'El mensaje no puede estar vacío'}, status=400)
            
            # 1. Enviar mensaje por WASender (opcional si falla)
            try:
                resp = WASenderService.send_message(contacto.telefono, texto)
                wasender_id = None
                if isinstance(resp, dict):
                    wasender_id = resp.get('data', {}).get('key', {}).get('id')
                
                if not wasender_id:
                     # Generamos un ID local robusto con UUID para evitar colisiones 100%
                     wasender_id = f"local_{uuid.uuid4().hex[:12]}_{contacto.id}"
            except Exception as e:
                logger.error(f"Error al enviar por WASender: {e}")
                # ID local de respaldo absoluto
                wasender_id = f"local_err_{uuid.uuid4().hex[:12]}"

            # 2. Guardar en Base de Datos
            nuevo_msg = ChatMensaje.objects.create(
                contacto=contacto,
                direccion='OUTBOUND',
                texto=texto,
                wasender_message_id=wasender_id,
                estado_envio='ENVIADO'
            )
            
            return JsonResponse({
                'success': True,
                'mensaje': {
                    'id': nuevo_msg.id,
                    'direccion': nuevo_msg.direccion,
                    'texto': nuevo_msg.texto,
                    'fecha': nuevo_msg.fecha_mensaje.strftime('%H:%M - %d/%m/%y'),
                    'estado': nuevo_msg.estado_envio
                }
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ClearChatHistoryAPIView(SupervisorChatMixin, View):
    """Elimina todos los mensajes de un contacto pero mantiene al contacto"""
    def post(self, request, contacto_id, *args, **kwargs):
        try:
            contacto = CrmContact.objects.get(id=contacto_id)
            mensajes = ChatMensaje.objects.filter(contacto=contacto)
            total = mensajes.count()
            mensajes.delete()
            return JsonResponse({'success': True, 'total_eliminados': total})
        except CrmContact.DoesNotExist:
            return JsonResponse({'error': 'Contacto no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

