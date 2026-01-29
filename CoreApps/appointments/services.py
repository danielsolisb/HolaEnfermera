from datetime import datetime, timedelta
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.crypto import get_random_string

# Importamos modelos
from CoreApps.appointments.models import Appointment, AppointmentStatus, AppointmentReminder
from CoreApps.services.models import Medication
from CoreApps.scheduling.models import NurseSchedule
from CoreApps.services.models import Service
from CoreApps.users.models import CustomerProfile
from CoreApps.notifications.services import NotificationService
from CoreApps.reports.models import ServiceFeedback
from CoreApps.notifications.services import WASenderService
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from email.mime.image import MIMEImage
import os


from django.db import models

User = get_user_model()

class AvailabilityService:
    """
    Motor de Disponibilidad V2: Marketplace.
    Devuelve bloques de horas AGRUPADOS por enfermero.
    """
    
    @staticmethod
    def obtener_disponibilidad_agrupada(fecha_consulta, servicio_id):
        """
        Retorna una lista de enfermeros, cada uno con sus horas libres.
        Estructura:
        [
            {'enfermero': {'id': 1, 'nombre': 'Juan'}, 'slots': ['08:00', '09:00']},
            {'enfermero': {'id': 2, 'nombre': 'Maria'}, 'slots': ['09:00', '10:00']}
        ]
        """
        servicio = Service.objects.get(id=servicio_id)
        duracion_horas = servicio.duracion_horas
        dia_semana = fecha_consulta.weekday() # 0=Lunes
        
        # 1. Buscar turnos vigentes para esa fecha (Específicos O Recurrentes)
        turnos = NurseSchedule.objects.filter(
            activo=True
        ).filter(
            Q(fecha_especifica=fecha_consulta) | 
            (Q(fecha_especifica__isnull=True) & Q(dia_semana=dia_semana))
        ).select_related('enfermero')

        resultados = []

        # Procesamos cada turno individualmente
        for turno in turnos:
            enfermero = turno.enfermero
            slots_enfermero = []
            
            # Definir límites del turno
            hora_actual = datetime.combine(fecha_consulta, turno.hora_inicio)
            fin_jornada = datetime.combine(fecha_consulta, turno.hora_fin)
            
            # Definir límites del almuerzo (si tiene)
            inicio_almuerzo = None
            fin_almuerzo = None
            if turno.descanso_inicio and turno.descanso_fin:
                inicio_almuerzo = datetime.combine(fecha_consulta, turno.descanso_inicio)
                fin_almuerzo = datetime.combine(fecha_consulta, turno.descanso_fin)

            # Buscar citas que YA tiene este enfermero ese día (Conflicto)
            citas_del_dia = Appointment.objects.filter(
                enfermero=enfermero,
                fecha=fecha_consulta,
                estado__nombre__in=['PENDIENTE', 'CONFIRMADA', 'EN_CAMINO', 'REAGENDADA']
            )

            # ITERAR BLOQUE POR BLOQUE (Cada 1 hora)
            while hora_actual + timedelta(hours=duracion_horas) <= fin_jornada:
                inicio_bloque = hora_actual
                fin_bloque = hora_actual + timedelta(hours=duracion_horas)
                
                es_viable = True
                
                # A. Chequeo de Almuerzo
                # Si el bloque toca el almuerzo en algún punto
                if inicio_almuerzo and fin_almuerzo:
                    # Se solapa si el inicio es antes del fin del almuerzo Y el fin es despues del inicio del almuerzo
                    if inicio_bloque < fin_almuerzo and fin_bloque > inicio_almuerzo:
                        es_viable = False
                
                # B. Chequeo de Citas Existentes
                if es_viable:
                    for cita in citas_del_dia:
                        # Convertir horas de cita a datetime completo para comparar
                        cita_inicio = datetime.combine(fecha_consulta, cita.hora_inicio)
                        # Usamos la hora fin calculada o asumimos 1h si fallara
                        if cita.hora_fin:
                            cita_fin = datetime.combine(fecha_consulta, cita.hora_fin)
                        else:
                            cita_fin = cita_inicio + timedelta(hours=1) # Fallback
                        
                        # Lógica de colisión de rangos
                        if inicio_bloque < cita_fin and fin_bloque > cita_inicio:
                            es_viable = False
                            break
                
                # C. Si pasó todas las pruebas, es un slot disponible
                if es_viable:
                    slots_enfermero.append(inicio_bloque.strftime("%H:%M"))
                
                # Avanzar al siguiente slot (Intervalo de 1 hora o 30 min)
                # Si quieres que las opciones sean 8:00, 9:00, 10:00 -> minutes=60
                # Si quieres 8:00, 8:30, 9:00 -> minutes=30
                hora_actual += timedelta(minutes=60)

            # Si el enfermero tiene al menos un hueco libre, lo agregamos a la lista final
            if slots_enfermero:
                resultados.append({
                    'enfermero': {
                        'id': enfermero.id,
                        'nombre': f"{enfermero.first_name} {enfermero.last_name}",
                        'foto': enfermero.foto.url if enfermero.foto else None,
                        # 'genero': enfermero.genero # Si lo agregaste, úsalo
                    },
                    'slots': slots_enfermero
                })

        return resultados


class BookingManager:
    """
    Gestor Central de Reservas y Leads.
    """
    
    @staticmethod
    @transaction.atomic
    def crear_cita_publica(datos_cliente, datos_cita):
        # ... (Este método ya lo tenías, déjalo igual) ...
        pass 

    @staticmethod
    @transaction.atomic
    @staticmethod
    def procesar_recordatorio_huerfano(datos_cliente, datos_lead):
        # MANTÉN ESTA FUNCIÓN COMO ESTABA
        # Se usa en: PublicReminderCreationAPIView (API externa)
        pass # (Aquí va tu código original)

    @staticmethod
    def procesar_recordatorio_completo(data):
        """
        NUEVA LÓGICA MEJORADA:
        - Guarda datos.
        - Envía WhatsApp detallado (Fecha calculada, Frecuencia, Agradecimiento Enfermero, Local).
        """
        from CoreApps.users.models import CustomerProfile
        
        # 1. GESTIÓN DE USUARIO
        cedula = data.get('cedula')
        email = data.get('email')
        user = User.objects.filter(models.Q(cedula=cedula) | models.Q(email=email)).first()
        
        usuario_es_nuevo = False
        password_temp = None

        if not user:
            usuario_es_nuevo = True
            username = email.split('@')[0] + "_" + cedula[-4:]
            password_temp = cedula 
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password_temp, 
                first_name=data.get('nombres'),
                last_name=data.get('apellidos'),
                cedula=cedula,
                telefono=data.get('telefono'),
                rol=User.Roles.CLIENTE
            )
        else:
            # Actualizamos datos de contacto por si cambiaron
            user.first_name = data.get('nombres')
            user.last_name = data.get('apellidos')
            user.telefono = data.get('telefono')
            user.save()

        # 2. GESTIÓN DE PERFIL
        perfil, created = CustomerProfile.objects.get_or_create(user=user)
        if data.get('fecha_nacimiento'):
            perfil.fecha_nacimiento = data.get('fecha_nacimiento')
        if data.get('ciudad'):
            perfil.ciudad = data.get('ciudad')
        perfil.save()

        # 3. GUARDAR RECORDATORIO (CÁLCULO AUTOMÁTICO DE FECHA)
        medicamento = None
        nombre_medicamento = data.get('medicamento_texto')
        
        if data.get('medicamento_id'):
            medicamento = Medication.objects.filter(id=data['medicamento_id']).first()
            if medicamento:
                nombre_medicamento = medicamento.nombre

        # Parsear fecha de aplicación si existe (viene como string del JSON)
        fecha_app_obj = None
        fecha_app_str = data.get('fecha_aplicacion')
        if fecha_app_str:
            try:
                # El input HTML date envía en formato YYYY-MM-DD
                fecha_app_obj = datetime.strptime(fecha_app_str, '%Y-%m-%d').date()
            except ValueError:
                # Fallback por seguridad
                fecha_app_obj = datetime.now().date()

        reminder = AppointmentReminder(
            paciente=user,
            medicamento_catalogo=medicamento,
            medicamento_externo=nombre_medicamento,
            origen='WEB',
            estado='PENDIENTE',
            fecha_ultima_aplicacion=fecha_app_obj, # Ahora pasamos un OBJETO fecha
            notas=f"Rating: {data.get('rating')}/5. Enfermero ID: {data.get('enfermero_id')}"
        )
        reminder.save() 
        # Al hacer save(), el modelo ya calculó 'fecha_limite_sugerida' internamente
        
        # 4. NOTIFICACIÓN POR CORREO (PACIENTE + ADMIN)
        try:
            # A. Preparar Contexto
            fecha_proxima = reminder.fecha_limite_sugerida
            texto_fecha = fecha_proxima.strftime('%d/%m/%Y') if fecha_proxima else "Por definir"
            
            texto_frecuencia = ""
            if medicamento:
                unidades = {'DIAS': 'días', 'MESES': 'meses', 'ANIOS': 'años'}
                unidad_legible = unidades.get(medicamento.frecuencia_unidad, medicamento.frecuencia_unidad)
                texto_frecuencia = f"(cada {medicamento.frecuencia_valor} {unidad_legible})"

            ciudad_cliente = perfil.ciudad if perfil.ciudad else "tu ciudad"

            contexto = {
                'paciente_nombre': user.first_name,
                'medicamento_nombre': nombre_medicamento,
                'fecha_proxima': texto_fecha,
                'frecuencia': texto_frecuencia,
                'ciudad': ciudad_cliente,
                'anio': datetime.now().year,
            }

            # B. Renderizar Template
            html_content = render_to_string('emails/reminder_created.html', contexto)
            text_content = f"Hola {user.first_name}, se ha creado un recordatorio para {nombre_medicamento} para el {texto_fecha}."

            # C. Obtener Destinatarios (Paciente + Admins)
            destinatarios = [user.email]
            admins = User.objects.filter(is_superuser=True, is_active=True).values_list('email', flat=True)
            destinatarios.extend(list(admins))

            # D. Crear Mensaje
            subject = f"Nuevo Recordatorio Creado: {nombre_medicamento}"
            msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, destinatarios)
            msg.attach_alternative(html_content, "text/html")

            # E. Adjuntar Logo (Inline)
            logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo-hola-enfermera.png')
            if os.path.exists(logo_path):
                with open(logo_path, 'rb') as f:
                    logo_data = f.read()
                    logo = MIMEImage(logo_data)
                    logo.add_header('Content-ID', '<logo_hola_enfermera>')
                    logo.add_header('Content-Disposition', 'inline', filename='logo-hola-enfermera.png')
                    msg.attach(logo)
            
            # F. Enviar
            msg.send()

        except Exception as e:
            print(f"⚠️ Error enviando correo de recordatorio: {e}")

        return reminder

    @staticmethod
    def create_next_cycle_reminder(reminder_actual):
        """
        Crea automáticamente el siguiente recordatorio para medicamentos recurrentes.
        Toma como base la fecha_limite_sugerida del recordatorio actual para mantener la precisión.
        """
        # 1. Validaciones previas
        if not reminder_actual.medicamento_catalogo or not reminder_actual.medicamento_catalogo.es_recurrente:
            return None

        # 2. Evitar duplicados: No crear si ya existe uno PENDIENTE para el mismo paciente y medicamento
        exists = AppointmentReminder.objects.filter(
            paciente=reminder_actual.paciente,
            medicamento_catalogo=reminder_actual.medicamento_catalogo,
            estado='PENDIENTE'
        ).exists()

        if exists:
            return None

        # 3. Crear el nuevo ciclo
        # Importante: Como 'base' usamos la fecha proyectada del anterior (ej: 27 de enero)
        # aunque el admin lo esté cerrando el 25 de enero.
        proxima_fecha_base = reminder_actual.fecha_limite_sugerida

        nuevo_recordatorio = AppointmentReminder(
            paciente=reminder_actual.paciente,
            medicamento_catalogo=reminder_actual.medicamento_catalogo,
            medicamento_externo=reminder_actual.medicamento_externo,
            origen='SISTEMA',
            estado='PENDIENTE',
            fecha_ultima_aplicacion=proxima_fecha_base, # Base para el nuevo cálculo
            notas=f"Ciclo automático generado desde recordatorio #{reminder_actual.id}."
        )
        
        # El save() del modelo se encargará de sumar la frecuencia (1 año, 6 meses, etc.)
        nuevo_recordatorio.save()
        
        return nuevo_recordatorio
