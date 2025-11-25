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



#----------------------------------------
class ReminderStep1View(View):
    """
    Paso 1: Qué y Cuándo.
    Captura medicamento y fecha. Guarda en sesión.
    """
    template_name = 'main/public_booking/reminder_step_1.html'

    def get(self, request):
        # Obtenemos medicamentos para el autocompletado (JSON)
        medicamentos = list(Medication.objects.filter(activo=True).values('id', 'nombre'))
        
        # Recuperamos datos previos si el usuario dio "Atrás"
        initial_data = request.session.get('wizard_data', {})
        
        context = {
            'medicamentos_json': medicamentos,
            'data': initial_data
        }
        return render(request, self.template_name, context)

    def post(self, request):
        # Guardamos en la sesión del navegador (temporalmente)
        request.session['wizard_data'] = {
            'medicamento_id': request.POST.get('medicamento_id'),
            'medicamento_texto': request.POST.get('medicamento_texto'),
            'fecha_aplicacion': request.POST.get('fecha_aplicacion'),
        }
        return redirect('public_reminder_step2')

class ReminderStep2View(View):
    """
    Paso 2: Calidad y Preferencia.
    Captura enfermero y rating. Guarda en sesión.
    """
    template_name = 'main/public_booking/reminder_step_2.html'

    def get(self, request):
        # Seguridad: Si no hay datos del paso 1, regresar
        if 'wizard_data' not in request.session:
            return redirect('public_reminder_step1')
            
        # Traemos los enfermeros activos para la selección visual
        enfermeros = User.objects.filter(rol='ENFERMERO', is_active=True)
        
        context = {
            'enfermeros': enfermeros,
            # No necesitamos pasar 'data' aquí porque los inputs son visuales/ocultos,
            # pero podrías hacerlo si quieres persistencia visual al volver.
        }
        return render(request, self.template_name, context)

    def post(self, request):
        # Recuperamos lo que ya teníamos
        data = request.session.get('wizard_data', {})
        
        # Agregamos lo nuevo
        data.update({
            'enfermero_id': request.POST.get('enfermero_id'),
            'rating': request.POST.get('rating'),
        })
        
        # Guardamos de nuevo en sesión
        request.session['wizard_data'] = data
        return redirect('public_reminder_step3')

class ReminderStep3View(View):
    """
    Paso 3: Datos Personales y Confirmación.
    Recibe datos finales, llama al Manager y guarda en BD.
    """
    template_name = 'main/public_booking/reminder_step_3.html'

    def get(self, request):
        if 'wizard_data' not in request.session:
            return redirect('public_reminder_step1')
        return render(request, self.template_name)

    def post(self, request):
        session_data = request.session.get('wizard_data', {})
        
        # Datos del Cliente (Vienen del POST actual)
        datos_cliente = {
            'cedula': request.POST.get('cedula'),
            'nombres': request.POST.get('nombres'),
            'apellidos': request.POST.get('apellidos'),
            'email': request.POST.get('email'),
            'telefono': request.POST.get('telefono'),
        }
        
        # Datos del Lead (Vienen de la sesión)
        datos_lead = {
            'medicamento_id': session_data.get('medicamento_id'),
            'medicamento_texto': session_data.get('medicamento_texto'),
            'fecha_aplicacion': session_data.get('fecha_aplicacion'),
            'enfermero_id': session_data.get('enfermero_id'),
            'rating': session_data.get('rating'),
        }

        try:
            # LLAMADA AL CEREBRO (Services.py)
            BookingManager.procesar_recordatorio_huerfano(datos_cliente, datos_lead)
            
            # Limpieza: Borrar datos de sesión para que no queden ahí
            if 'wizard_data' in request.session:
                del request.session['wizard_data']
            
            return redirect('public_reminder_success')
            
        except Exception as e:
            # Si falla, mostramos el error en la misma página
            print(f"Error procesando lead: {e}")
            return render(request, self.template_name, {'error': str(e)})

class ReminderSuccessView(View):
    template_name = 'main/public_booking/success.html'
    
    def get(self, request):
        return render(request, self.template_name)
