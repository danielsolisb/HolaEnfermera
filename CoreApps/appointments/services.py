from datetime import datetime, timedelta
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.crypto import get_random_string

# Importamos modelos
from CoreApps.appointments.models import Appointment, AppointmentStatus
from CoreApps.scheduling.models import NurseSchedule
from CoreApps.services.models import Service
from CoreApps.users.models import CustomerProfile
from CoreApps.notifications.services import NotificationService
from CoreApps.reports.models import ServiceFeedback

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
    def procesar_recordatorio_huerfano(datos_cliente, datos_lead):
        """
        Procesa el formulario de 'Recordatorio + Calificación'.
        1. Busca/Crea Cliente.
        2. Calcula fecha futura basada en fecha_aplicacion pasada.
        3. Crea AppointmentReminder.
        4. Crea ServiceFeedback (Calificación).
        """
        
        # 1. GESTIÓN DE USUARIO (Idéntico a crear cita)
        email = datos_cliente.get('email')
        cedula = datos_cliente.get('cedula')
        
        usuario = User.objects.filter(Q(email=email) | Q(cedula=cedula)).first()
        
        if not usuario:
            password_temporal = get_random_string(length=8)
            usuario = User.objects.create_user(
                username=email,
                email=email,
                password=password_temporal,
                first_name=datos_cliente.get('nombres'),
                last_name=datos_cliente.get('apellidos'),
                cedula=cedula,
                telefono=datos_cliente.get('telefono'),
                rol=User.Roles.CLIENTE
            )
            CustomerProfile.objects.create(user=usuario)
            # Opcional: Enviar correo de bienvenida aquí también
        
        # 2. CÁLCULO DE FECHA (La lógica de la dueña)
        fecha_aplicacion_str = datos_lead.get('fecha_aplicacion') # "2023-11-20"
        medicamento_id = datos_lead.get('medicamento_id')
        medicamento_texto = datos_lead.get('medicamento_texto')
        
        fecha_limite = None
        medicamento_obj = None
        
        if fecha_aplicacion_str and medicamento_id:
            try:
                fecha_app = datetime.strptime(fecha_aplicacion_str, "%Y-%m-%d").date()
                medicamento_obj = Medication.objects.get(id=medicamento_id)
                
                # Lógica de cálculo según unidad
                val = medicamento_obj.frecuencia_valor
                uni = medicamento_obj.frecuencia_unidad
                
                if uni == 'DIAS':
                    fecha_limite = fecha_app + timedelta(days=val)
                elif uni == 'MESES': # Aproximación simple +30 días por mes
                    fecha_limite = fecha_app + timedelta(days=val*30) 
                elif uni == 'ANIOS':
                    fecha_limite = fecha_app.replace(year=fecha_app.year + val)
            except Exception as e:
                print(f"Error calculando fecha: {e}")
                # Si falla, se queda en None y la dueña lo pone manual.

        # 3. CREAR RECORDATORIO
        reminder = AppointmentReminder.objects.create(
            paciente=usuario,
            origen='WEB',
            medicamento_catalogo=medicamento_obj,
            medicamento_externo=medicamento_texto, # Por si puso "Otro"
            fecha_limite_sugerida=fecha_limite,
            estado='PENDIENTE',
            notas=f"Lead captado desde web. Última aplicación reportada: {fecha_aplicacion_str}"
        )
        
        # 4. CREAR CALIFICACIÓN (FEEDBACK)
        enfermero_id = datos_lead.get('enfermero_id')
        rating = datos_lead.get('rating') # 1 a 5
        
        if enfermero_id and rating:
            try:
                enfermero = User.objects.get(id=enfermero_id, rol='ENFERMERO')
                ServiceFeedback.objects.create(
                    paciente=usuario,
                    enfermero=enfermero,
                    rating=int(rating),
                    origen='WEB_HUERFANO',
                    comentario="Calificación recibida durante registro de recordatorio."
                )
                # Aquí vinculamos la preferencia al recordatorio para cerrar el círculo
                reminder.enfermero_sugerido = enfermero
                reminder.save()
                
            except User.DoesNotExist:
                pass # Si el ID no es válido, ignoramos la calificación pero guardamos el lead
                
        return reminder