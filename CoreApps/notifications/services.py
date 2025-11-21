from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

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