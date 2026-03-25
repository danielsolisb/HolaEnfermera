from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

import requests
import json
import re
import os
import mimetypes
from django.conf import settings

logger = logging.getLogger(__name__)

class NotificationService:
    
    @staticmethod
    def enviar_bienvenida_usuario(usuario, password_generada):
        """
        Envía el correo de bienvenida con la contraseña temporal.
        """
        asunto = "Bienvenido a Hola Enfermera - Tu Cuenta ha sido Creada"
        mensaje = f"""
        Hola {usuario.first_name},
        
        Gracias por agendar tu cita con nosotros. Hemos creado una cuenta para ti.
        
        Tus credenciales de acceso son:
        Usuario (Email): {usuario.email}
        Contraseña Temporal: {password_generada}
        
        Por favor, ingresa al sistema y cambia tu contraseña lo antes posible.
        
        Atentamente,
        El equipo de Hola Enfermera
        """
        
        # Si quieres usar HTML en el futuro, aquí podrías cargar un template
        # html_message = render_to_string('emails/welcome.html', context)
        
        try:
            send_mail(
                subject=asunto,
                message=mensaje,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[usuario.email],
                fail_silently=False,
            )
            logger.info(f"Correo de bienvenida enviado a {usuario.email}")
            return True
        except Exception as e:
            logger.error(f"Error enviando correo a {usuario.email}: {e}")
            return False

class WASenderService:
    """
    Servicio para WASenderAPI usando autenticación Bearer y el endpoint /api/send-message.
    Adaptado de wasenderapi_utils.py
    """

    @staticmethod
    def upload_media(file_path):
        """
        Sube un archivo físico a WASender y retorna la publicUrl.
        """
        api_key = settings.WASENDERAPI_API_KEY
        if not api_key: return None
        
        api_url = "https://wasenderapi.com/api/upload"
        headers = {
            'Authorization': f'Bearer {api_key}',
        }

        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'

            logger.info(f"Subiendo archivo a WASender: {file_path} ({mime_type})")
            print(f"📁 [WASender-Upload] Subiendo: {os.path.basename(file_path)} ({mime_type})")
            
            with open(file_path, 'rb') as f:
                raw_headers = headers.copy()
                raw_headers['Content-Type'] = mime_type
                response = requests.post(api_url, headers=raw_headers, data=f, timeout=60)
                
            print(f"📡 [WASender-Upload] Status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            
            if data.get('success'):
                public_url = data.get('publicUrl')
                print(f"✅ [WASender-Upload] Éxito. URL: {public_url}")
                return public_url
            
            print(f"❌ [WASender-Upload] Falla: {response.text}")
            logger.error(f"Falla en respuesta de upload: {data}")
            return None
        except Exception as e:
            print(f"❌ [WASender-Upload] EXCEPCIÓN: {e}")
            logger.error(f"Error subiendo archivo a WASender: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Detalle API: {e.response.text}")
            return None

    @staticmethod
    def send_media(phone_number, media_url, caption="", media_type="IMAGE", file_path=None):
        """
        Envía un archivo multimedia (imagen, video, documento) vía WASender.
        Si file_path existe, primero lo sube para obtener una publicUrl válida (necesario para localhost).
        """
        api_key = settings.WASENDERAPI_API_KEY
        if not api_key: return False
        
        effective_url = media_url
        if file_path and os.path.exists(file_path):
            uploaded_url = WASenderService.upload_media(file_path)
            if uploaded_url:
                effective_url = uploaded_url
        
        api_url = "https://www.wasenderapi.com/api/send-message"
        formatted_number = WASenderService._format_phone_number(phone_number)
        if not formatted_number: return False

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        
        # Construcción de PAYLOAD HÍBRIDO para máxima compatibilidad
        payload = {
            'to': formatted_number,
        }
        
        # SÓLO enviar 'text' si tiene contenido real (evita error 422 de cadena vacía)
        if caption and caption.strip():
            payload['text'] = caption

        # Atributos específicos tipados (según docs /api-docs/messages/send-...)
        # Para AUDIO nativo WASenderAPI recomienda a veces un endpoint /api/messages/send-audio-message
        # pero también soportan audioUrl en la ruta general para ciertos engines.
        if media_type == 'IMAGE':
            payload['imageUrl'] = effective_url
        elif media_type == 'VIDEO':
            payload['videoUrl'] = effective_url
        elif media_type == 'AUDIO':
            payload['audioUrl'] = effective_url
            api_url = "https://wasenderapi.com/api/send-message"
            payload['audio'] = effective_url # Alternativa en caso que requiera la key directa
        elif media_type == 'DOCUMENT':
            payload['documentUrl'] = effective_url
            payload['fileName'] = os.path.basename(file_path) if file_path else "documento"

        # Atributos genéricos de compatibilidad (algunas versiones los prefieren)
        payload['media_url'] = effective_url
        payload['media_type'] = media_type.lower()

        print(f"🚀 [WASender-SendMedia] Enviando {media_type} a {formatted_number}")
        print(f"🔗 URL: {effective_url}")
        print(f"📦 Payload Híbrido: {json.dumps(payload, indent=2)}")

        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            print(f"📡 [WASender-SendMedia] Status: {response.status_code}")
            print(f"📄 Respuesta: {response.text}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ [WASender-SendMedia] EXCEPCIÓN: {e}")
            logger.error(f"Error enviando media a {formatted_number}: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Detalle API WASender: {e.response.text}")
            return False

    @staticmethod
    def _format_phone_number(phone_number):
        """
        Formatea el número asegurando el prefijo +593 para Ecuador.
        Retorna el número con formato +593XXXXXXXXX.
        """
        if not phone_number:
            return None
        
        # Limpiar todo lo que no sea dígitos
        cleaned = re.sub(r'[^\d]', '', str(phone_number))
        
        # Lógica específica para Ecuador (móviles empiezan con 09)
        if cleaned.startswith('09') and len(cleaned) == 10:
            return '+593' + cleaned[1:]
        
        # Si ya tiene 593 (12 dígitos), agregar el +
        if cleaned.startswith('593') and len(cleaned) == 12:
            return '+' + cleaned
            
        # Si no cumple, retornamos lo que hay con un + por si acaso es internacional
        return '+' + cleaned

    @staticmethod
    def send_location(phone_number, lat, lng, name="Ubicación", address=""):
        """
        Envía una ubicación geográfica (Globo) vía WASender (Endpoint Nativo).
        """
        api_key = settings.WASENDERAPI_API_KEY
        if not api_key: return False
        
        api_url = "https://wasenderapi.com/api/send-message"
        formatted_number = WASenderService._format_phone_number(phone_number)
        if not formatted_number: return False

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'to': formatted_number,
            'location': {
                'latitude': float(lat),
                'longitude': float(lng),
                'name': str(name),
                'address': str(address)
            }
        }
        
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error enviando ubicación a {formatted_number}: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"WASender: {e.response.text}")
            return False

    @staticmethod
    def send_message(phone_number, message):
        """
        Envía mensaje usando Authorization: Bearer y payload {'to', 'text'}.
        """
        # 1. VALIDAR API KEY
        api_key = settings.WASENDERAPI_API_KEY
        if not api_key:
            logger.error("WASender: API Key no configurada en settings.")
            print("❌ WASender: Falta API Key")
            return False

        # 2. URL EXACTA (Hardcodeada según tu ejemplo funcional para evitar errores de .env)
        # Si prefieres usar el .env, asegúrate que sea la base correcta, pero esto es más seguro por ahora.
        api_url = "https://wasenderapi.com/api/send-message"

        # 3. FORMATEAR NÚMERO
        formatted_number = WASenderService._format_phone_number(phone_number)
        if not formatted_number:
            logger.warning("WASender: Número inválido.")
            print("❌ WASender: Número inválido")
            return False

        # 4. PREPARAR PETICIÓN (HEADERS Y PAYLOAD)
        headers = {
            'Authorization': f'Bearer {api_key}',  # <--- CLAVE DEL ÉXITO
            'Content-Type': 'application/json',
        }
        
        payload = {
            'to': formatted_number, # Debe llevar el '+' según tu utils
            'text': message
        }

        # --- DEBUG EN CONSOLA ---
        print("\n" + "="*30)
        print("🚀 INTENTANDO ENVIAR WHATSAPP (BEARER)")
        print(f"URL: {api_url}")
        print(f"Para: {formatted_number}")
        print(f"Header Auth: Bearer {api_key[:10]}...")
        
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=20)
            
            # --- DEBUG RESPUESTA ---
            print(f"📡 STATUS CODE: {response.status_code}")
            print(f"📄 RESPUESTA: {response.text}")
            print("="*30 + "\n")

            response.raise_for_status()
            response_data = response.json()

            # Verificación de éxito según tu utils
            if response.status_code in [200, 201] and response_data.get('success') is True:
                logger.info(f"WASender: Mensaje enviado a {formatted_number}")
                return response_data # Devolvemos todo el dict para sacar el message ID
            else:
                logger.error(f"WASender Falló: {response.text}")
                return False

        except Exception as e:
            logger.error(f"WASender Error: {e}")
            print(f"❌ ERROR EXCEPCIÓN: {e}")
            print("="*30 + "\n")
            return False