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
                ahora_local = timezone.localtime(ahora)
                hoy = ahora_local.date()
                manana = hoy + datetime.timedelta(days=1)
                
                # Formato log
                prefix = f"[{ahora_local.strftime('%d/%m/%Y %H:%M')}]"

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

                    hubo_actividad = False

                    # =================================================================
                    # FASE 2: DETECCCION DE COLA (Pendientes para Mañana)
                    # =================================================================
                    cola_envio = AppointmentReminder.objects.filter(
                        fecha_limite_sugerida=manana,
                        estado__in=['PENDIENTE', 'FALLO_ENVIO'] 
                    ).order_by('id')

                    total_cola = cola_envio.count()

                    if total_cola > 0:
                        self.stdout.write(f"{prefix} 📨 Encolados para mañana ({manana}): {total_cola} mensajes.")
                        hubo_actividad = True
                        
                        # Para no bloquear, solo procesamos los recordatorios uno a uno con sleep
                        for recordatorio in cola_envio:
                            paciente = recordatorio.paciente
                            telefono = paciente.telefono
                            nombre = f"{paciente.first_name}"
                            tema = str(recordatorio)
                            
                            mensaje = f"👋 Hola {nombre}, te recordamos que mañana cumple la fecha para: *{tema}*.\n\n"
                            mensaje += "Por favor, contáctanos para agendar tu visita o coordinar el servicio.\n"
                            mensaje += "Somos Hola Enfermera 💙."

                            self.stdout.write(f"   👉 Procesando Recordatorio: {paciente}...")

                            exito = False
                            respuesta = ""
                            
                            try:
                                resp_service = WASenderService.send_message(telefono, mensaje)
                                exito = True
                                respuesta = str(resp_service)
                            except Exception as e:
                                exito = False
                                respuesta = f"Error: {str(e)}"
                                self.stdout.write(self.style.ERROR(f"      ❌ Fallo envío: {e}"))

                            if exito:
                                recordatorio.estado = 'CONTACTADO'
                                recordatorio.save()
                                self.stdout.write(self.style.SUCCESS(f"      ✅ Recordatorio Enviado."))
                            else:
                                recordatorio.estado = 'FALLO_ENVIO' 
                                recordatorio.save()

                            NotificationLog.objects.create(
                                recordatorio=recordatorio,
                                enviado=exito,
                                respuesta_api=respuesta
                            )

                            self.stdout.write(f"      ⏳ Esperando 5 minutos (Recordatorios)...")
                            time.sleep(300) 
                    
                    # =================================================================
                    # FASE 3: DETECCIÓN DE CAMPAÑAS DE MARKETING
                    # =================================================================
                    from django.db.models import Q
                    from CoreApps.crm_marketing.models import MensajeCampana

                    campanas_activas = MensajeCampana.objects.filter(
                        estado='PENDIENTE',
                        campana__estado__in=['PROGRAMADA', 'ENVIANDO']
                    ).filter(
                        Q(campana__fecha_programada__isnull=True) | Q(campana__fecha_programada__lte=ahora)
                    ).order_by('id')

                    total_campanas = campanas_activas.count()
                    
                    if total_campanas > 0:
                        hubo_actividad = True
                        self.stdout.write(f"{prefix} 📢 Campañas en cola: {total_campanas} mensajes pendientes.")
                        
                        # Procesamos solo de 10 en 10 para volver rápido a revisar si hay recordatorios médicos
                        lote = campanas_activas[:10]
                        for msg in lote:
                            # Marcar campaña general como enviando
                            if msg.campana.estado != 'ENVIANDO':
                                msg.campana.estado = 'ENVIANDO'
                                msg.campana.save(update_fields=['estado'])
                            
                            telefono = msg.contacto.telefono
                            plantilla = msg.campana.mensaje_plantilla
                            
                            # Reemplazos dinámicos avanzados
                            datos_contacto = {
                                '{nombres}': msg.contacto.nombres or '',
                                '{apellidos}': msg.contacto.apellidos or '',
                                '{ciudad}': msg.contacto.ciudad.nombre if msg.contacto.ciudad else '',
                                '{farmacia}': msg.contacto.farmacia_origen.nombre if msg.contacto.farmacia_origen else '',
                                '{telefono}': msg.contacto.telefono or '',
                            }
                            
                            texto_final = plantilla
                            for tag, valor in datos_contacto.items():
                                if tag in texto_final:
                                    texto_final = texto_final.replace(tag, valor)
                            
                            self.stdout.write(f"   👉 Campaña ({msg.campana.nombre}) a {telefono}...")
                            
                            exito = False
                            try:
                                resp_service = WASenderService.send_message(telefono, texto_final)
                                if isinstance(resp_service, dict):
                                    exito = True
                                    try:
                                        msg.wasender_message_id = resp_service.get('data', {}).get('key', {}).get('id', '')
                                    except:
                                        pass
                                elif resp_service == True:
                                    exito = True
                            except Exception as e:
                                msg.error_log = str(e)
                            
                            if exito:
                                msg.estado = 'ENVIADO'
                                self.stdout.write(self.style.SUCCESS(f"      ✅ Masivo Enviado."))
                                
                                # --- NUEVO: Sincronizar con el historial de Chat CRM ---
                                try:
                                    import uuid
                                    from CoreApps.chat.models import ChatMensaje
                                    
                                    w_id = msg.wasender_message_id
                                    if not w_id:
                                        w_id = f"local_camp_{uuid.uuid4().hex[:12]}"
                                        
                                    ChatMensaje.objects.create(
                                        contacto=msg.contacto,
                                        direccion='OUTBOUND',
                                        texto=texto_final,
                                        wasender_message_id=w_id,
                                        estado_envio='ENVIADO'
                                    )
                                except Exception as e_sync:
                                    self.stdout.write(self.style.ERROR(f"      ⚠️ Error sincronizando chat: {e_sync}"))
                                # ------------------------------------------------------
                            else:
                                msg.estado = 'ERROR'
                                self.stdout.write(self.style.ERROR(f"      ❌ Masivo Fallido."))
                            
                            msg.save()
                            
                            # Retardo anti-spam de campañas (Más corto porque son muchos)
                            self.stdout.write(f"      ⏳ Esperando 25s (Anti-Spam)...")
                            time.sleep(25)
                            
                        # Actualizar estado a COMPLETADA si ya no hay pendientes
                        for c in set([m.campana for m in lote]):
                            restantes = MensajeCampana.objects.filter(campana=c, estado='PENDIENTE').count()
                            if restantes == 0:
                                c.estado = 'COMPLETADA'
                                c.save(update_fields=['estado'])
                                self.stdout.write(self.style.SUCCESS(f"🎯 Campaña '{c.nombre}' FINALIZADA."))

                    # =================================================================
                    # REPOSO
                    # =================================================================
                    if not hubo_actividad:
                        self.stdout.write(f"{prefix} 💤 Nada pendiente (Recordatorios o Campañas). Durmiendo 30 segundos...")
                        time.sleep(30)

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"🔥 CRITICAL ERROR EN WORKER: {e}"))
                    time.sleep(60)

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n🛑 Worker detenido por el usuario (Ctrl+C).'))
