from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils import timezone, timezone as dj_timezone
from django.db import models, transaction
from django.db.models import Max
from django.http import JsonResponse, HttpResponseRedirect, StreamingHttpResponse, FileResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.conf import settings
import os
import requests
import uuid
import datetime
import logging
import json

from CoreApps.crm_marketing.models import MensajeCampana, CrmContact
from .models import WhatsAppConversation, WhatsAppMessage, ChatMensaje

logger = logging.getLogger(__name__)

class SupervisorChatMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Permite acceso a personal de marketing y ventas (staff) al inbox"""
    def test_func(self):
        return self.request.user.is_staff


class InboxView(SupervisorChatMixin, TemplateView):
    template_name = 'chat/inbox.html'

    def get_context_data(self, **kwargs):
        # --- LIMPIEZA AUTOMÁTICA DE REGISTROS CORRUPTOS ('' -> None) ---
        ChatMensaje.objects.filter(wasender_message_id='').update(wasender_message_id=None)
        # -------------------------------------------------------------

        context = super().get_context_data(**kwargs)
        # Obtenemos contactos que tengan historial de chat, ordenados por el último mensaje
        
        contactos_con_chat = CrmContact.objects.filter(historial_chat__isnull=False).annotate(
            ultimo_msg_fecha=Max('historial_chat__fecha_mensaje')
        ).order_by('-ultimo_msg_fecha')
        
        from CoreApps.crm_marketing.models import CrmConfig, CrmMediaTemplate
        context['crm_config'] = CrmConfig.get_solo()
        context['media_templates'] = CrmMediaTemplate.objects.all()
        
        # Si viene un contact_id por URL, lo pasamos al contexto para que el JS lo abra
        context['auto_open_contact_id'] = self.request.GET.get('contact_id')
        
        return context


@method_decorator(csrf_exempt, name='dispatch')
class WasenderWebhookView(View):
    """
    Recibe los eventos desde WASenderAPI (ej. message.sent, message.read)
    Documentación oficial: https://wasenderapi.com/api-docs/webhooks/webhook-setup
    """
    def post(self, request, *args, **kwargs):
        try:
            # 1. Verificación de Seguridad (opcional si está configurado en .env)
            if hasattr(settings, 'WASENDER_WEBHOOK_SECRET') and settings.WASENDER_WEBHOOK_SECRET:
                signature = request.headers.get('X-Webhook-Signature')
                if signature != settings.WASENDER_WEBHOOK_SECRET:
                    logger.warning(f"Intento de webhook con firma inválida. Recibida: {signature}")
                    return JsonResponse({'error': 'Invalid signature'}, status=401)
            payload = json.loads(request.body)
            try:
                import os, json as local_json
                debug_path = os.path.join(settings.BASE_DIR, 'logs_webhook_debug.json')
                with open(debug_path, 'a', encoding='utf-8') as f:
                    f.write(local_json.dumps(payload) + "\n---\n")
            except Exception as e:
                logger.error(f"Error saving debug: {e}")
            if not isinstance(payload, dict):
                return JsonResponse({'error': 'Invalid payload format'}, status=400)
                
            event = payload.get('event')

            # 2. Manejo de prueba de conexión
            if event == 'webhook.test':
                return JsonResponse({'received': True, 'msg': 'Connection successful'}, status=200)
            
            data = payload.get('data', {})
            if not isinstance(data, (dict, list)):
                return JsonResponse({'status': 'ok'})

            # 3. Procesamiento de Mensajes (Nuevos o Actualizados)
            if event in ['message.sent', 'messages.update', 'message.read', 'message.ack', 'message-receipt.update']:
                self._handle_status_updates(event, data)
            
            elif event in ['messages.upsert', 'messages.received', 'message.received']:
                # Soporte para variaciones de nombre de evento
                messages_to_process = []
                if (event == 'messages.upsert') and isinstance(data, dict):
                    # WASender puede enviar dict o list en 'messages'
                    msgs = data.get('messages', [])
                    messages_to_process = msgs if isinstance(msgs, list) else [msgs]
                else:
                    # Caso messages.received o similar donde data es el objeto
                    messages_to_process = [data] if isinstance(data, dict) else []
                
                for msg_data in messages_to_process:
                    self._save_whatsapp_message(msg_data)
            
            elif event in ['contacts.upsert', 'contacts.update']:
                self._handle_contact_sync(data)
            
            else:
                pass # Evento ignorado
            
            return JsonResponse({'status': 'ok'})
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error procesando webhook de WASender: {e}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

    def _handle_contact_sync(self, data):
        """Sincroniza nombres de contactos desde la agenda de WhatsApp"""
        try:
            contacts_list = data if isinstance(data, list) else [data]
            for c_data in contacts_list:
                jid = c_data.get('id', '')
                name = c_data.get('name') or c_data.get('notify')
                
                lid = c_data.get('lid')
                
                if not jid or not name: continue
                if '@g.us' in jid: continue
                
                # Buscar contacto por JID o por Teléfono
                telefono_puro = jid.split('@')[0]
                if not telefono_puro.startswith('+'):
                    telefono_puro = f"+{telefono_puro}"
                
                from django.db.models import Q
                query = Q(whatsapp_jid=jid) | Q(telefono=telefono_puro)
                if lid:
                    query |= Q(whatsapp_lid=lid)
                
                contacto = CrmContact.objects.filter(query).first()
                if contacto:
                    updated_fields = []
                    if lid and contacto.whatsapp_lid != lid:
                        contacto.whatsapp_lid = lid
                        updated_fields.append('whatsapp_lid')
                        
                    # Solo actualizar si el nombre actual es genérico o vacío
                    if not contacto.nombres or "Hola Enfermera" in contacto.nombres or "Contacto WhatsApp" in contacto.nombres or "Nuevo Contacto" in contacto.nombres:
                        contacto.nombres = name
                        updated_fields.append('nombres')
                        
                    # Autocuración del Teléfono: Si el teléfono actual es un LID (muy largo) y el JID es un número real
                    if not '@lid' in jid and jid != '':
                        if not contacto.telefono or len(contacto.telefono) > 13 or contacto.telefono.startswith('+2'):
                            if contacto.telefono != telefono_puro:
                                contacto.telefono = telefono_puro
                                updated_fields.append('telefono')
                                
                        if not contacto.whatsapp_jid or '@lid' in contacto.whatsapp_jid:
                            contacto.whatsapp_jid = jid
                            updated_fields.append('whatsapp_jid')
                        
                    if updated_fields:
                        contacto.save(update_fields=updated_fields)
                        logger.info(f"Contacto actualizado desde agenda: {name} ({telefono_puro})")
        except Exception as e:
            logger.error(f"Error en _handle_contact_sync: {e}")

    def _handle_status_updates(self, event, data):
        """Maneja el rastro de lectura/entrega para campañas y chat en vivo"""
        updates = data if isinstance(data, list) else [data]
        for upd in updates:
            if not isinstance(upd, dict): continue
            key = upd.get('key', {})
            wasender_id = key.get('id')
            if wasender_id:
                status_str = upd.get('update', {}).get('status', '').upper()
                
                # Mapeo robusto de estados de WASender
                # 3 = Delivered (Check Gris), 4 o 'READ' = Read (Check Azul)
                if status_str in ['READ', 'SEEN', '4'] or 'read' in str(event).lower():
                    nuevo_estado = 'LEIDO'
                elif status_str in ['DELIVERED', '3']:
                    nuevo_estado = 'ENTREGADO'
                else:
                    nuevo_estado = 'ENVIADO'
                
                # Actualizar para campañas
                MensajeCampana.objects.filter(wasender_message_id=wasender_id).update(estado=nuevo_estado)
                
                # Actualizar para el chat en vivo
                ChatMensaje.objects.filter(wasender_message_id=wasender_id).update(estado_envio=nuevo_estado)

    def _save_whatsapp_message(self, msg_data):
        """Procesa y guarda un mensaje individual en el CrmContact y ChatMensaje"""
        try:
            if not isinstance(msg_data, dict): return
            
            # WASender a veces mete el mensaje dentro de una clave 'messages' incluso en eventos individuales
            if 'messages' in msg_data and isinstance(msg_data['messages'], dict):
                msg_data = msg_data['messages']
            
            key = msg_data.get('key', {})
            if not isinstance(key, dict): return
            
            from_me = key.get('fromMe', False)
            
            # Identificación del teléfono
            remote_jid = key.get('remoteJid', '')
            
            if not from_me:
                # Si lo envía el cliente, su tel puede venir en senderPn si JID es oculto (LID)
                sender_pn = key.get('senderPn', '') or msg_data.get('senderPn', '')
                target_jid = sender_pn if sender_pn else remote_jid
            else:
                # Si lo enviamos nosotros, remoteJid es el chat del cliente
                target_jid = remote_jid
                
            if not target_jid or '@g.us' in target_jid: return 
            
            # Formatear teléfono
            telefono_puro = target_jid.split('@')[0]
            if not telefono_puro.startswith('+'):
                telefono_puro = f"+{telefono_puro}"
            
            if telefono_puro == '+': # No procesar si no hay número
                return

            # Extraer texto del cuerpo o del objeto message
            message_content = msg_data.get('message', {})
            if not isinstance(message_content, dict): message_content = {}
            
            text_content = (message_content.get('conversation') or 
                           message_content.get('extendedTextMessage', {}).get('text') or 
                           msg_data.get('messageBody') or
                           "[Media/Otro formato]")
            
            wasender_id = key.get('id', '') or msg_data.get('id', '')

            # 2. Buscar/Crear contacto con bloqueo de fila para evitar duplicados concurrentes
            with transaction.atomic():
                # Normalizar para búsqueda
                telefono_busqueda = remote_jid.split('@')[0]
                if not telefono_busqueda.startswith('+'):
                    telefono_busqueda = '+' + telefono_busqueda
                
                # Intentamos obtener el contacto con bloqueo de fila
                contacto = None
                # 1. Buscar por LID y por Teléfono/JID simultáneamente
                contacto_por_lid = None
                if '@lid' in remote_jid:
                    contacto_por_lid = CrmContact.objects.filter(whatsapp_lid=remote_jid).select_for_update().first()
                
                contacto_por_jid = None
                if target_jid and '@s.whatsapp.net' in target_jid:
                    tel_busqueda = '+' + target_jid.split('@')[0]
                    from django.db.models import Q
                    contacto_por_jid = CrmContact.objects.filter(Q(telefono=tel_busqueda) | Q(whatsapp_jid=target_jid)).select_for_update().first()
                elif not '@lid' in target_jid:
                    # En caso de que target_jid sea ya un teléfono puro
                    tel_busqueda = target_jid if target_jid.startswith('+') else '+' + target_jid.split('@')[0]
                    contacto_por_jid = CrmContact.objects.filter(telefono=tel_busqueda).select_for_update().first()

                # 2. Lógica de Fusión (Auto-Sanación) de Fantasmas
                contacto = None
                if contacto_por_lid and contacto_por_jid and contacto_por_lid.id != contacto_por_jid.id:
                    # Se detectó un fantasma (creado por LID) y el contacto real (JID).
                    # Fusionamos el historial del fantasma hacia el contacto real.
                    ChatMensaje.objects.filter(contacto=contacto_por_lid).update(contacto=contacto_por_jid)
                    
                    update_fields = []
                    if not contacto_por_jid.whatsapp_lid:
                        contacto_por_jid.whatsapp_lid = contacto_por_lid.whatsapp_lid
                        update_fields.append('whatsapp_lid')
                    if not contacto_por_jid.whatsapp_jid:
                        contacto_por_jid.whatsapp_jid = target_jid
                        update_fields.append('whatsapp_jid')
                    if update_fields:
                        contacto_por_jid.save(update_fields=update_fields)
                        
                    contacto_por_lid.delete()
                    contacto = contacto_por_jid
                elif contacto_por_jid:
                    contacto = contacto_por_jid
                elif contacto_por_lid:
                    contacto = contacto_por_lid

                # 3. Creación o Actualización si no hubo fusión
                if not contacto:
                    # Crear nuevo contacto
                    nombres_wa = msg_data.get('pushName') if not from_me else None
                    if not nombres_wa or "Hola Enfermera" in nombres_wa:
                        nombres_wa = "Nuevo Contacto"

                    tel_final = target_jid.split('@')[0] if target_jid else remote_jid.split('@')[0]
                    if not tel_final.startswith('+'):
                        tel_final = '+' + tel_final

                    lid_val = remote_jid if '@lid' in remote_jid else None
                    jid_val = target_jid if '@s.whatsapp.net' in target_jid else None

                    contacto = CrmContact.objects.create(
                        nombres=nombres_wa,
                        apellidos="",
                        telefono=tel_final,
                        whatsapp_jid=jid_val,
                        whatsapp_lid=lid_val,
                        es_organico=True,
                    )
                else:
                    # Actualizar info si es necesario (ej: si antes no tenía JID o el nombre era genérico)
                    updated_fields = []
                    
                    if '@lid' in remote_jid and contacto.whatsapp_lid != remote_jid:
                        contacto.whatsapp_lid = remote_jid
                        updated_fields.append('whatsapp_lid')
                    elif '@s.whatsapp.net' in remote_jid and contacto.whatsapp_jid != remote_jid:
                        contacto.whatsapp_jid = remote_jid
                        updated_fields.append('whatsapp_jid')
                    
                    # Autosanador en sitio para "huérfanos" 
                    if not from_me and target_jid and '@s.whatsapp.net' in target_jid:
                        real_phone = '+' + target_jid.split('@')[0]
                        if not contacto.telefono or (len(contacto.telefono) > 13 and not contacto.telefono.startswith('+5')):
                            # Si es un contacto que no pudo fusionarse (porque no existía), pero acaba de darnos su número:
                            contacto.telefono = real_phone
                            updated_fields.append('telefono')
                            if not contacto.whatsapp_jid:
                                contacto.whatsapp_jid = target_jid
                                updated_fields.append('whatsapp_jid')

                    if not from_me:
                        push_name = msg_data.get('pushName')
                        nombres_genericos = ["Hola Enfermera", "Contacto WhatsApp", "Nuevo Contacto"]
                        if push_name and push_name not in nombres_genericos and (not contacto.nombres or any(g in contacto.nombres for g in nombres_genericos)):
                            contacto.nombres = push_name
                            updated_fields.append('nombres')
                    
                    if updated_fields:
                        contacto.save(update_fields=updated_fields)

                # --- Lógica de Autonomía y Trazabilidad (Fase 25 y 33) ---
                now = timezone.now()
                contacto.fecha_ultima_actividad = now
                contact_updated = True
                
                if not from_me:
                    # Mensaje ENTRANTE: 
                    # 1. Marcar inicio de Lead si no lo tiene
                    if not contacto.fecha_creacion_lead:
                        contacto.fecha_creacion_lead = now
                    
                    # 2. Lógica de Re-Apertura (Fase 33)
                    # Si el contacto estaba en una etapa finalizada y vuelve a escribir, lo regresamos a Lead
                    etapas_finales = ['GANADO', 'PERDIDO', 'DESCARTADO']
                    if contacto.etapa_comercial in etapas_finales:
                        contacto.etapa_comercial = 'LEAD'
                        contacto.fecha_creacion_lead = now # Reiniciar contador de sangre fría para el nuevo interés
                        contacto.fecha_primer_contacto = None # Resetear para medir nueva respuesta
                else:
                    # Mensaje SALIENTE (Desde CRM o Móvil): Mover etapa y registrar respuesta
                    if contacto.etapa_comercial == 'LEAD':
                        contacto.etapa_comercial = 'CONTACTADO'
                    
                    if not contacto.fecha_primer_contacto:
                        contacto.fecha_primer_contacto = now
                        if contacto.fecha_creacion_lead:
                            contacto.tiempo_respuesta_inicial = now - contacto.fecha_creacion_lead

                if contact_updated:
                    contacto.save()
            
            # 2. Guardar Mensaje
            if wasender_id:
                # Detección de Multimedia
                media_url = None
                media_type = 'TEXT'
                media_key = None
                mimetype = None
                
                if 'audioMessage' in message_content:
                    media_type = 'AUDIO'
                    msg_obj = message_content['audioMessage']
                    media_url = msg_obj.get('url')
                    media_key = msg_obj.get('mediaKey')
                    mimetype = msg_obj.get('mimetype', 'audio/ogg')
                    text_content = "[🎙️ Mensaje de voz]"
                elif 'imageMessage' in message_content:
                    media_type = 'IMAGE'
                    msg_obj = message_content['imageMessage']
                    media_url = msg_obj.get('url')
                    media_key = msg_obj.get('mediaKey')
                    mimetype = msg_obj.get('mimetype', 'image/jpeg')
                    text_content = "[📷 Imagen]"
                elif 'videoMessage' in message_content:
                    media_type = 'VIDEO'
                    msg_obj = message_content['videoMessage']
                    media_url = msg_obj.get('url')
                    media_key = msg_obj.get('mediaKey')
                    mimetype = msg_obj.get('mimetype', 'video/mp4')
                    text_content = "[🎥 Video]"
                elif 'documentMessage' in message_content:
                    media_type = 'DOCUMENT'
                    msg_obj = message_content['documentMessage']
                    media_url = msg_obj.get('url')
                    media_key = msg_obj.get('mediaKey')
                    mimetype = msg_obj.get('mimetype', 'application/pdf')
                    text_content = f"[📄 Documento: {msg_obj.get('fileName', 'Archivo')}]"
                elif 'locationMessage' in message_content or 'liveLocationMessage' in message_content:
                    media_type = 'TEXT' # O LOCATION si tuvieras soporte de enum, pero TEXT evita crasheos.
                    msg_obj = message_content.get('locationMessage') or message_content.get('liveLocationMessage')
                    lat = msg_obj.get('degreesLatitude')
                    lon = msg_obj.get('degreesLongitude')
                    name = msg_obj.get('name', 'Ubicación')
                    address = msg_obj.get('address', '')
                    media_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                    mimetype = 'text/location'
                    
                    texto_construido = f"[📍 Ubicación] {name}"
                    if address: texto_construido += f" - {address}"
                    text_content = texto_construido
                    # Lo guardamos como TEXT pero aprovechamos media_url para el link de Maps.

                # Deduplicación para mensajes salientes (evitar doble confirmación de webhook)
                import datetime
                if from_me and wasender_id:
                    tiempo_limite = timezone.now() - datetime.timedelta(minutes=2)
                    query = ChatMensaje.objects.filter(
                        contacto=contacto,
                        direccion='OUTBOUND',
                        wasender_message_id__startswith='local_',
                        fecha_mensaje__gte=tiempo_limite
                    )
                    
                    if media_type == 'TEXT':
                        query = query.filter(texto=text_content)
                    else:
                        query = query.filter(media_type=media_type)
                        
                    msg_preexistente = query.order_by('fecha_mensaje').first()
                    
                    if msg_preexistente:
                        # Reemplazamos el ID temporal local por el Real de WhatsApp para enrutar el estado de Envío correctamente
                        from django.db import IntegrityError
                        msg_preexistente.wasender_message_id = wasender_id
                        msg_preexistente.estado_envio = 'ENTREGADO'
                        try:
                            msg_preexistente.save(update_fields=['wasender_message_id', 'estado_envio'])
                        except IntegrityError:
                            # Si hubo conflicto, ya existía, por tanto lo ignoramos o eliminamos el temporal
                            msg_preexistente.delete()
                        return

                # Si no existía, usar update_or_create para manejar reintentos de webhook transparentemente
                ChatMensaje.objects.update_or_create(
                    wasender_message_id=wasender_id,
                    defaults={
                        'contacto': contacto,
                        'direccion': 'OUTBOUND' if from_me else 'INBOUND',
                        'texto': text_content,
                        'media_url': media_url,
                        'media_type': media_type,
                        'media_key': media_key,
                        'mimetype': mimetype,
                        'estado_envio': 'ENTREGADO'
                    }
                )
        except Exception as e:
            logger.error(f"Error en _save_whatsapp_message: {e}", exc_info=True)


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
            fecha_str = ''
            if ultimo_mensaje:
                fecha_local = timezone.localtime(ultimo_mensaje.fecha_mensaje)
                fecha_str = fecha_local.strftime('%d/%m %H:%M')
                
            data.append({
                'id': c.id,
                'nombre': f"{c.nombres} {c.apellidos}",
                'telefono': c.display_phone,
                'is_hidden': c.is_hidden_number,
                'ultimo_mensaje': ultimo_mensaje.texto if ultimo_mensaje else '',
                'fecha_ultimo': fecha_str,
                'direccion_ultimo': ultimo_mensaje.direccion if ultimo_mensaje else '',
                'no_leido': not ultimo_mensaje.leido_por_operador if ultimo_mensaje and ultimo_mensaje.direccion == 'INBOUND' else False,
                'es_organico': c.es_organico,
                'campanas': c.get_campanas_nombres(),
                'es_proveedor': c.es_proveedor
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
            fecha_local = timezone.localtime(m.fecha_mensaje)
            data.append({
                'id': m.id,
                'direccion': m.direccion,
                'texto': m.texto,
                'media_url': m.media_url,
                'media_type': m.media_type,
                'mimetype': m.mimetype,
                'fecha': fecha_local.strftime('%H:%M - %d/%m/%y'),
                'estado': m.estado_envio
            })
        return JsonResponse({
            'contacto': {
                'id': contacto.id,
                'nombre': f"{contacto.nombres} {contacto.apellidos}",
                'telefono': contacto.telefono,
                'es_organico': contacto.es_organico,
                'campanas': contacto.get_campanas_nombres()
            },
            'mensajes': data
        })

@method_decorator(csrf_exempt, name='dispatch')
class ChatSendAPIView(SupervisorChatMixin, View):
    """Endpoint para enviar un mensaje manualmente (Texto o Multimedia)"""
    def post(self, request, contacto_id, *args, **kwargs):
        try:
            contacto = CrmContact.objects.get(id=contacto_id)
            payload = json.loads(request.body)
            texto = payload.get('texto', '').strip()
            media_id = payload.get('media_id')
            
            if not texto and not media_id:
                return JsonResponse({'error': 'El mensaje no puede estar vacío'}, status=400)

            # Resolución de Plantilla Multimedia
            media_template = None
            if media_id:
                from CoreApps.crm_marketing.models import CrmMediaTemplate
                try:
                    media_template = CrmMediaTemplate.objects.get(id=media_id)
                except CrmMediaTemplate.DoesNotExist:
                    return JsonResponse({'error': 'Plantilla multimedia no encontrada'}, status=404)
            
            # 1. Enviar mensaje por WASender
            wasender_id = None
            try:
                if media_template:
                    # Construir URL absoluta para que WASender pueda descargar el archivo
                    media_url = request.build_absolute_uri(media_template.archivo.url)
                    resp = WASenderService.send_media(
                        contacto.telefono, 
                        media_url, 
                        caption=texto, 
                        media_type=media_template.tipo,
                        file_path=media_template.archivo.path
                    )
                else:
                    resp = WASenderService.send_message(contacto.telefono, texto)
                
                if isinstance(resp, dict):
                    # Intentamos extraer el ID de mensaje de la respuesta estructurada de WASender
                    wasender_id = resp.get('data', {}).get('key', {}).get('id')
                
                if not wasender_id:
                    wasender_id = f"local_{uuid.uuid4().hex[:12]}_{contacto.id}"

            except Exception as e:
                logger.error(f"Error al enviar por WASender: {e}")
                wasender_id = f"local_err_{uuid.uuid4().hex[:12]}"

            # 2. Guardar en Base de Datos
            nuevo_msg = ChatMensaje.objects.create(
                contacto=contacto,
                direccion='OUTBOUND',
                texto=texto if not media_template else (texto or media_template.nombre),
                media_url=media_template.archivo.url if media_template else None,
                media_type=media_template.tipo if media_template else 'TEXT',
                wasender_message_id=wasender_id,
                estado_envio='ENVIADO'
            )
            
            return JsonResponse({
                'success': True,
                'mensaje': {
                    'id': nuevo_msg.id,
                    'direccion': nuevo_msg.direccion,
                    'texto': nuevo_msg.texto,
                    'media_url': nuevo_msg.media_url,
                    'media_type': nuevo_msg.media_type,
                    'fecha': nuevo_msg.fecha_mensaje.strftime('%H:%M - %d/%m/%y'),
                    'estado': nuevo_msg.estado_envio
                }
            })
            
        except Exception as e:
            logger.error(f"Excepción en ChatSendAPIView: {e}")
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ChatSendLocationAPIView(SupervisorChatMixin, View):
    """Endpoint explícito para enviar coordenadas geográficas vía WASender."""
    def post(self, request, contacto_id, *args, **kwargs):
        try:
            contacto = CrmContact.objects.get(id=contacto_id)
            payload = json.loads(request.body)
            lat = payload.get('lat')
            lng = payload.get('lng')
            name = payload.get('name', 'Ubicación Enviada')
            address = payload.get('address', '')
            
            if not lat or not lng:
                return JsonResponse({'error': 'Faltan coordenadas'}, status=400)
                
            # Llamar al WASenderService
            wasender_id = None
            try:
                resp = WASenderService.send_location(contacto.telefono, lat, lng, name, address)
                if isinstance(resp, dict):
                    wasender_id = resp.get('data', {}).get('key', {}).get('id')
                if not wasender_id:
                    wasender_id = f"local_loc_{uuid.uuid4().hex[:10]}"
            except Exception as e:
                logger.error(f"Error enviando ubicación WASender: {e}")
                wasender_id = f"local_err_{uuid.uuid4().hex[:10]}"
                
            # Guardar estáticamente como TEXT + mimetype de ubicación
            import datetime
            nuevo_msg = ChatMensaje.objects.create(
                contacto=contacto,
                direccion='OUTBOUND',
                texto=f"[📍 Ubicación Enviada] {name}",
                media_url=f"https://www.google.com/maps/search/?api=1&query={lat},{lng}",
                media_type='TEXT',
                mimetype='text/location',
                wasender_message_id=wasender_id,
                estado_envio='ENVIADO'
            )
            
            return JsonResponse({
                'success': True,
                'mensaje': {
                    'id': nuevo_msg.id,
                    'direccion': nuevo_msg.direccion,
                    'texto': nuevo_msg.texto,
                    'media_url': nuevo_msg.media_url,
                    'media_type': nuevo_msg.media_type,
                    'mimetype': nuevo_msg.mimetype,
                    'fecha': timezone.localtime(nuevo_msg.fecha_mensaje).strftime('%H:%M - %d/%m/%y'),
                    'estado': nuevo_msg.estado_envio
                }
            })
        except Exception as e:
            logger.error(f"Excepción en ChatSendLocationAPIView: {e}")
            return JsonResponse({'error': str(e)}, status=500)

from django.core.files.storage import FileSystemStorage

@method_decorator(csrf_exempt, name='dispatch')
class ChatSendVoiceNoteAPIView(SupervisorChatMixin, View):
    """Sube y envía una nota de voz grabada en el frontend"""
    def post(self, request, contacto_id, *args, **kwargs):
        try:
            contacto = CrmContact.objects.get(id=contacto_id)
            if 'audio' not in request.FILES:
                return JsonResponse({'error': 'No se recibió ningún archivo de audio'}, status=400)
            
            audio_file = request.FILES['audio']
            
            # Guardamos el archivo temporalmente
            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'voicenotes'))
            filename = fs.save(f"vn_{uuid.uuid4().hex[:8]}.ogg", audio_file)
            file_url = fs.url(filename)
            file_path = fs.path(filename)
            
            public_url = request.build_absolute_uri(f"/media/voicenotes/{filename}")
            
            wasender_id = None
            try:
                # Utilizamos send_media que internamente hace el upload a wasender
                resp = WASenderService.send_media(contacto.telefono, public_url, caption="", media_type="AUDIO", file_path=file_path)
                if isinstance(resp, dict):
                    wasender_id = resp.get('data', {}).get('key', {}).get('id')
                if not wasender_id:
                    wasender_id = f"local_vn_{uuid.uuid4().hex[:10]}"
            except Exception as e:
                logger.error(f"Error enviando nota de voz WASender: {e}")
                wasender_id = f"local_err_{uuid.uuid4().hex[:10]}"
                
            nuevo_msg = ChatMensaje.objects.create(
                contacto=contacto,
                direccion='OUTBOUND',
                texto="[🎙️ Nota de Voz Enviada]",
                media_url=public_url,
                media_type='AUDIO',
                mimetype='audio/ogg',
                wasender_message_id=wasender_id,
                estado_envio='ENVIADO'
            )
            
            return JsonResponse({
                'success': True,
                'mensaje': {
                    'id': nuevo_msg.id,
                    'direccion': nuevo_msg.direccion,
                    'texto': nuevo_msg.texto,
                    'media_url': nuevo_msg.media_url,
                    'media_type': nuevo_msg.media_type,
                    'mimetype': nuevo_msg.mimetype,
                    'fecha': timezone.localtime(nuevo_msg.fecha_mensaje).strftime('%H:%M - %d/%m/%y'),
                    'estado': nuevo_msg.estado_envio
                }
            })
        except Exception as e:
            logger.error(f"Excepción en ChatSendVoiceNoteAPIView: {e}")
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
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class MediaProxyView(SupervisorChatMixin, View):
    """
    Vista Proxy que decripta un archivo multimedia de WhatsApp usando la API de WASender
    y sirve el contenido directamente (Streaming) para evitar problemas de .enc y 0:00.
    """
    def get(self, request, mensaje_id, *args, **kwargs):
        from django.http import HttpResponseRedirect
        try:
            mensaje = ChatMensaje.objects.get(id=mensaje_id)
            
            # --- BYPASS LOCAL PARA ARCHIVOS SALIENTES (OUTBOUND) ---
            # Si el mensaje lo enviamos nosotros, sabemos que es nuestro propio archivo sin encriptar
            if mensaje.direccion == 'OUTBOUND' and mensaje.media_url:
                if 'ngrok' in mensaje.media_url or '/media/' in mensaje.media_url or getattr(settings, 'DOMAIN_URL', '') in mensaje.media_url:
                    return HttpResponseRedirect(mensaje.media_url)

            if not mensaje.media_url or not mensaje.media_key:
                logger.warning(f"Multimedia no decriptable para mensaje {mensaje_id} (posiblemente antiguo)")
                return JsonResponse({'error': 'Multimedia no decriptable'}, status=404)
            
            # 1. Determinar el tipo de mensaje para el payload de WASender
            # El payload requiere que la llave coincida con el tipo de mensaje de WhatsApp
            type_map = {
                'AUDIO': 'audioMessage',
                'IMAGE': 'imageMessage',
                'VIDEO': 'videoMessage',
                'DOCUMENT': 'documentMessage'
            }
            msg_key = type_map.get(mensaje.media_type, 'documentMessage')

            # 2. Preparar payload ESTRUCTURADO según documentación oficial
            payload = {
                "data": {
                    "messages": {
                        "key": {
                            "id": mensaje.wasender_message_id or "unknown_id"
                        },
                        "message": {
                            msg_key: {
                                "url": mensaje.media_url,
                                "mediaKey": mensaje.media_key,
                                "mimetype": mensaje.mimetype or "application/octet-stream"
                            }
                        }
                    }
                }
            }
            
            # 2. CACHÉ LOCAL: Verificamos si el archivo ya fue decriptado y guardado antes
            cache_dir = os.path.join(settings.MEDIA_ROOT, 'wasender_cache')
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir, exist_ok=True)
            
            # Generar nombre de archivo basado en ID y mimetype
            extension = 'bin'
            if mensaje.mimetype:
                if 'audio' in mensaje.mimetype: extension = 'ogg'
                elif 'image' in mensaje.mimetype: extension = 'jpg'
                elif 'video' in mensaje.mimetype: extension = 'mp4'
                elif 'pdf' in mensaje.mimetype: extension = 'pdf'
                elif '/' in mensaje.mimetype: extension = mensaje.mimetype.split('/')[-1]

            cache_filename = f"msg_{mensaje_id}.{extension}"
            cache_path = os.path.join(cache_dir, cache_filename)

            if os.path.exists(cache_path):
                logger.info(f"Sirviendo desde caché local: {cache_filename}")
                response = FileResponse(open(cache_path, 'rb'), content_type=mensaje.mimetype)
                if mensaje.media_type == 'DOCUMENT':
                    response['Content-Disposition'] = f'inline; filename="documento_{mensaje_id}.pdf"'
                return response

            # 3. Llamada a la API de decriptación si no está en caché
            api_key = settings.WASENDER_API_KEY
            base_url = settings.WASENDER_BASE_URL.rstrip('/')
            decrypt_endpoint = f"{base_url}/decrypt-media"
            
            # Construir el payload anidado según la nueva documentación oficial
            media_msg_key = "imageMessage"
            if mensaje.media_type == 'AUDIO': media_msg_key = "audioMessage"
            elif mensaje.media_type == 'VIDEO': media_msg_key = "videoMessage"
            elif mensaje.media_type == 'DOCUMENT': media_msg_key = "documentMessage"
            
            payload = {
                "data": {
                    "messages": {
                        "key": {
                            "id": mensaje.wasender_message_id or f"temp_{uuid.uuid4()}"
                        },
                        "message": {
                            media_msg_key: {
                                "url": mensaje.media_url,
                                "mimetype": mensaje.mimetype or "application/octet-stream",
                                "mediaKey": mensaje.media_key
                            }
                        }
                    }
                }
            }

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Iniciando decriptación para mensaje {mensaje_id} (Endpoint: /decrypt-media)")
            resp_init = requests.post(decrypt_endpoint, json=payload, headers=headers, timeout=15)
            
            if resp_init.status_code == 200:
                data = resp_init.json()
                # La documentación confirma que la clave es 'publicUrl'
                public_url = data.get('publicUrl')
                
                if not public_url:
                    logger.error(f"Falla en respuesta WASender (publicUrl no encontrado): {data}")
                    return JsonResponse({'error': 'No se obtuvo URL decriptada'}, status=500)

                # 4. DESCARGA Y CACHEO: Descargamos el archivo, lo guardamos y lo servimos
                logger.info(f"Descargando y cacheando multimedia desde: {public_url}")
                media_resp = requests.get(public_url, stream=True, timeout=30)
                
                if media_resp.status_code == 200:
                    with open(cache_path, 'wb') as f:
                        for chunk in media_resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    logger.info(f"Archivo guardado en caché: {cache_filename}")
                    response = FileResponse(open(cache_path, 'rb'), content_type=mensaje.mimetype)
                    if mensaje.media_type == 'DOCUMENT':
                        response['Content-Disposition'] = f'inline; filename="documento_{mensaje_id}.pdf"'
                    return response
                else:
                    return JsonResponse({'error': 'Error al descargar el archivo decriptado'}, status=media_resp.status_code)
            else:
                # Si falla decriptación y no está en caché (ej: mensaje muy antiguo)
                logger.warning(f"Multimedia no decriptable para mensaje {mensaje_id}: {resp_init.status_code} - {resp_init.text}")
                return JsonResponse({'error': 'El archivo multimedia ya no está disponible en WhatsApp'}, status=404)
                
        except ChatMensaje.DoesNotExist:
            return JsonResponse({'error': 'Mensaje no encontrado'}, status=404)
        except Exception as e:
            logger.error(f"Fallo crítico en MediaProxyView: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)

