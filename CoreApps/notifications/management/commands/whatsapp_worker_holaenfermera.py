import time
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from CoreApps.appointments.models import AppointmentReminder
from CoreApps.notifications.models import NotificationLog
from CoreApps.notifications.services import WASenderService

class Command(BaseCommand):
    help = 'Worker unificado que envía recordatorios a pacientes un día antes.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('✅ [Worker] Iniciando servicio de notificaciones...'))
        
        try:
            while True:
                # 1. Definir Fechas Clave (Zona Horaria Local del Server)
                ahora = timezone.now()
                hoy = ahora.date()
                manana = hoy + datetime.timedelta(days=1)
                
                # Formato log
                prefix = f"[{ahora.strftime('%d/%m/%Y %H:%M')}]"

                try:
                    # =================================================================
                    # FASE 1: LIMPIEZA DE EXPIRADOS (Mantenimiento)
                    # =================================================================
                    # Si un recordatorio PENDIENTE tiene fecha menor a hoy, ya expiró.
                    expirados = AppointmentReminder.objects.filter(
                        estado='PENDIENTE',
                        fecha_limite_sugerida__lt=hoy
                    )
                    count_exp = expirados.count()
                    if count_exp > 0:
                        expirados.update(estado='EXPIRADO')
                        self.stdout.write(f"{prefix} 🧹 Limpieza: {count_exp} recordatorios marcados como EXPIRADO.")

                    # =================================================================
                    # FASE 2: DETECCCION DE COLA (Pendientes para Mañana)
                    # =================================================================
                    # Buscamos PENDIENTE o FALLO_ENVIO (si quisiéramos reintentar) para MAÑANA
                    # NOTA: Solo procesamos los de 'mañana'. Los de 'hoy' o pasados ya caen en expirados o manual.
                    
                    cola_envio = AppointmentReminder.objects.filter(
                        fecha_limite_sugerida=manana,
                        estado__in=['PENDIENTE', 'FALLO_ENVIO'] # Incluimos FALLO por si se repara el error
                    ).order_by('id')

                    total_cola = cola_envio.count()

                    if total_cola > 0:
                        self.stdout.write(f"{prefix} 📨 Encolados para mañana ({manana}): {total_cola} mensajes.")
                        
                        for recordatorio in cola_envio:
                            paciente = recordatorio.paciente
                            telefono = paciente.telefono
                            nombre = f"{paciente.first_name}"
                            tema = str(recordatorio)
                            
                            # Mensaje Personalizado
                            mensaje = f"👋 Hola {nombre}, te recordamos que mañana cumple la fecha para: *{tema}*.\n\n"
                            mensaje += "Por favor, contáctanos para agendar tu visita o coordinar el servicio.\n"
                            mensaje += "Somos Hola Enfermera 💙."

                            self.stdout.write(f"   👉 Procesando: {paciente}...")

                            # --- INTENTO DE ENVÍO ---
                            exito = False
                            respuesta = ""
                            
                            try:
                                # Llamada al servicio
                                resp_service = WASenderService.send_message(telefono, mensaje)
                                exito = True # Si no lanza excepción, asumimos True (según tu servicio)
                                respuesta = str(resp_service)
                            except Exception as e:
                                exito = False
                                respuesta = f"Error: {str(e)}"
                                self.stdout.write(self.style.ERROR(f"      ❌ Fallo envío: {e}"))

                            # --- ACTUALIZACIÓN DE ESTADO ---
                            if exito:
                                recordatorio.estado = 'CONTACTADO'
                                recordatorio.save()
                                self.stdout.write(self.style.SUCCESS(f"      ✅ Enviado correctamente."))
                            else:
                                recordatorio.estado = 'FALLO_ENVIO' 
                                recordatorio.save()

                            # --- LOG DE AUDITORÍA ---
                            NotificationLog.objects.create(
                                recordatorio=recordatorio,
                                enviado=exito,
                                respuesta_api=respuesta
                            )

                            # --- RATE LIMITING (5 MINUTOS) ---
                            # Solo esperamos si hubo envío (o intento). 
                            self.stdout.write(f"      ⏳ Esperando 5 minutos por seguridad anti-spam...")
                            time.sleep(300) 
                    
                    else:
                        # Si no hay nada que hacer, dormimos un rato para no quemar CPU
                        # Revisar cada 1 hora si hay nuevos
                        self.stdout.write(f"{prefix} 💤 Nada pendiente para mañana. Durmiendo 1 hora...")
                        time.sleep(3600)

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"🔥 CRITICAL ERROR EN WORKER: {e}"))
                    time.sleep(60) # Espera 1 min antes de reiniciar el loop para no spamear errores

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n🛑 Worker detenido por el usuario (Ctrl+C).'))
