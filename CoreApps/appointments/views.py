import json
from datetime import datetime
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt # Necesario si la landing está fuera, o manejamos CSRF token en template
from django.conf import settings
from django.views.generic import TemplateView
from CoreApps.services.models import Medication

from .services import AvailabilityService, BookingManager
from CoreApps.services.models import Service

from django.shortcuts import render, redirect


from django.contrib.auth import get_user_model
from CoreApps.users.models import User




class AvailabilityAPIView(View):
    """
    API Pública: Devuelve horarios disponibles agrupados por enfermero.
    Uso: GET /api/availability/?fecha=2023-11-20&servicio_id=1
    """
    def get(self, request):
        fecha_str = request.GET.get('fecha')
        servicio_id = request.GET.get('servicio_id')

        if not fecha_str or not servicio_id:
            return JsonResponse({'error': 'Faltan parámetros fecha o servicio_id'}, status=400)

        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            
            # Llamamos a tu MOTOR DE DISPONIBILIDAD
            data = AvailabilityService.obtener_disponibilidad_agrupada(fecha, servicio_id)
            
            return JsonResponse({'status': 'success', 'disponibilidad': data})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch') # Solo si la petición viene de fuera sin token. Si es interno, quitar esto.
class PublicBookingAPIView(View):
    """
    API Pública: Recibe datos del formulario y crea la reserva.
    Uso: POST /api/book/ con JSON body
    """
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            # Separamos los datos como espera tu BookingManager
            datos_cliente = data.get('cliente')
            datos_cita = data.get('cita')

            if not datos_cliente or not datos_cita:
                return JsonResponse({'error': 'Estructura JSON inválida. Se requiere "cliente" y "cita".'}, status=400)

            # Llamamos a tu GESTOR DE RESERVAS
            cita = BookingManager.crear_cita_publica(datos_cliente, datos_cita)

            return JsonResponse({
                'status': 'success', 
                'cita_id': cita.id,
                'mensaje': 'Cita creada y usuario notificado.'
            })

        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        except Exception as e:
            # Loggear error real en consola
            print(f"Error Booking: {e}") 
            return JsonResponse({'status': 'error', 'message': 'Error interno al procesar la reserva.'}, status=500)
    
@method_decorator(csrf_exempt, name='dispatch')
class PublicReminderCreationAPIView(View):
    """
    API Pública: Recibe el formulario de 'Recordatorio Huérfano'.
    JSON esperado:
    {
        "cliente": { ... },
        "lead": {
            "medicamento_id": 1,
            "fecha_aplicacion": "2023-11-24",
            "enfermero_id": 5,
            "rating": 5
        }
    }
    """
    def post(self, request):
        try:
            data = json.loads(request.body)
            datos_cliente = data.get('cliente')
            datos_lead = data.get('lead')

            if not datos_cliente or not datos_lead:
                return JsonResponse({'error': 'Datos incompletos'}, status=400)

            # Llamamos a la nueva lógica del cerebro
            BookingManager.procesar_recordatorio_huerfano(datos_cliente, datos_lead)

            return JsonResponse({
                'status': 'success', 
                'message': 'Recordatorio y calificación guardados correctamente.'
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

class LeadReminderWizardView(TemplateView):
    """
    Vista principal del Wizard de Recordatorios (Público).
    Carga la plantilla y los datos iniciales para el JS.
    """
    template_name = 'main/public_booking/reminder_wizard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pasamos los medicamentos activos para el autocompletado
        context['medicamentos'] = Medication.objects.filter(activo=True).values('id', 'nombre', 'descripcion')
        return context


class CheckUserAPIView(View):
    def get(self, request):
        cedula = request.GET.get('cedula')
        if not cedula:
            return JsonResponse({'exists': False})
        
        try:
            user = User.objects.get(cedula=cedula, rol='CLIENTE')
            
            # Intentamos obtener el perfil (puede que no exista si es un usuario antiguo)
            perfil = getattr(user, 'perfil_cliente', None)
            
            data = {
                'exists': True,
                'user': {
                    'nombres': user.first_name,
                    'apellidos': user.last_name,
                    'email': user.email,
                    'telefono': user.telefono,
                    # Datos del Perfil (si existen)
                    'fecha_nacimiento': perfil.fecha_nacimiento.strftime('%Y-%m-%d') if (perfil and perfil.fecha_nacimiento) else '',
                    'ciudad': perfil.ciudad if perfil else '',
                }
            }
            return JsonResponse(data)
        except User.DoesNotExist:
            return JsonResponse({'exists': False})

#----------------------------------------

class ReminderExperienceView(View):
    """
    NUEVO PASO 1: Captura Medicamento, Fecha, Enfermero y Calificación.
    """
    template_name = 'main/public_booking/reminder_experience.html'

    def get(self, request):
        # 1. Obtener Medicamentos para el buscador
        medicamentos = list(Medication.objects.filter(activo=True).values('id', 'nombre'))
        
        # 2. Obtener Enfermeros para la selección
        enfermeros = User.objects.filter(rol='ENFERMERO', is_active=True)
        
        # 3. Recuperar datos si el usuario da "Atrás"
        initial_data = request.session.get('wizard_data', {})
        
        context = {
            'medicamentos_json': medicamentos,
            'enfermeros': enfermeros,
            'data': initial_data,
            'step': 1 # Para la barra de progreso
        }
        return render(request, self.template_name, context)

    def post(self, request):
        # Guardamos TODO en la sesión de una sola vez
        request.session['wizard_data'] = {
            # Datos de Medicamento
            'medicamento_id': request.POST.get('medicamento_id'),
            'medicamento_texto': request.POST.get('medicamento_texto'),
            'fecha_aplicacion': request.POST.get('fecha_aplicacion'),
            
            # Datos de Enfermero y Rating
            'enfermero_id': request.POST.get('enfermero_id'),
            'rating': request.POST.get('rating'),
        }
        # Redirigimos al nuevo Paso 2
        return redirect('public_reminder_patient')

class ReminderPatientView(View):
    """
    NUEVO PASO 2: Datos Personales + Perfil (Cumpleaños/Ciudad)
    """
    # Usaremos una nueva plantilla para ser ordenados
    template_name = 'main/public_booking/reminder_patient.html' 
    
    def get(self, request):
        if 'wizard_data' not in request.session:
            return redirect('public_reminder_experience')
        return render(request, self.template_name, {'step': 2})

    def post(self, request):
        session_data = request.session.get('wizard_data', {})
        
        # 1. Recopilar datos del Formulario Actual (Paso 2)
        datos_paciente = {
            'cedula': request.POST.get('cedula'),
            'nombres': request.POST.get('nombres'),
            'apellidos': request.POST.get('apellidos'),
            'email': request.POST.get('email'),
            'telefono': request.POST.get('telefono'),
            # Nuevos campos de Perfil
            'fecha_nacimiento': request.POST.get('fecha_nacimiento'),
            'ciudad': request.POST.get('ciudad'),
        }
        
        # 2. Fusionar con datos del Paso 1 (Experiencia)
        datos_completos_lead = {
            **session_data, # (Medicamento, Fecha, Enfermero, Rating)
            **datos_paciente
        }

        try:
            # 3. Llamar al Cerebro (BookingManager)
            # Nota: Hemos cambiado ligeramente la firma del método, ver Paso 4
            BookingManager.procesar_recordatorio_completo(datos_completos_lead)
            
            # 4. Limpieza y Éxito
            if 'wizard_data' in request.session:
                del request.session['wizard_data']
            
            return redirect('public_reminder_success')
            
        except Exception as e:
            print(f"Error procesando lead: {e}")
            # Devolver el error a la plantilla para que el usuario sepa qué pasó
            return render(request, self.template_name, {'step': 2, 'error': str(e), 'data': datos_paciente})

class ReminderSuccessView(View):
    template_name = 'main/public_booking/success.html'
    
    def get(self, request):
        # Pasamos 'step': 3 para indicar que todo el proceso finalizó
        return render(request, self.template_name, {'step': 3})