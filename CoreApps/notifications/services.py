from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

import requests
import json
import re
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