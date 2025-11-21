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
    Gestor de Reservas Públicas.
    """
    @staticmethod
    @transaction.atomic
    def crear_cita_publica(datos_cliente, datos_cita):
        # 1. Gestión de Usuario (Busca o Crea)
        email = datos_cliente.get('email')
        cedula = datos_cliente.get('cedula')
        
        usuario = User.objects.filter(Q(email=email) | Q(cedula=cedula)).first()
        es_nuevo = False
        password_temporal = None
        
        if not usuario:
            es_nuevo = True
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
            
            CustomerProfile.objects.create(
                user=usuario,
                direccion=datos_cliente.get('direccion', ''),
                ciudad=datos_cliente.get('ciudad', ''),
                google_maps_link=datos_cliente.get('google_maps_link', '')
            )
        
        # 2. Obtener objetos
        servicio = Service.objects.get(id=datos_cita['servicio_id'])
        fecha = datetime.strptime(datos_cita['fecha'], "%Y-%m-%d").date()
        hora = datetime.strptime(datos_cita['hora'], "%H:%M").time()
        
        # ASIGNACIÓN EXPLÍCITA: El cliente eligió a UN enfermero específico
        enfermero_id = datos_cita.get('enfermero_id')
        enfermero = User.objects.get(id=enfermero_id, rol='ENFERMERO') if enfermero_id else None
        
        # 3. Crear Cita
        # Buscamos el estado PENDIENTE (asegúrate que exista en BD)
        estado_pendiente, _ = AppointmentStatus.objects.get_or_create(nombre='PENDIENTE')
        
        cita = Appointment.objects.create(
            paciente=usuario,
            servicio=servicio,
            enfermero=enfermero, # Aquí guardamos al que eligió el cliente
            estado=estado_pendiente,
            fecha=fecha,
            hora_inicio=hora,
            tipo_ubicacion=datos_cita.get('tipo_ubicacion', 'DOMICILIO'),
            latitud=datos_cita.get('latitud'),
            longitud=datos_cita.get('longitud'),
            notas=datos_cita.get('notas', ''),
            cliente_tiene_insumos=datos_cita.get('tiene_insumos', False)
        )
        
        # 4. Notificaciones
        if es_nuevo and password_temporal:
            NotificationService.enviar_bienvenida_usuario(usuario, password_temporal)
            
        return cita