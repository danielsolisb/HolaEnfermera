import json
from datetime import datetime
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt # Necesario si la landing está fuera, o manejamos CSRF token en template
from django.conf import settings

from .services import AvailabilityService, BookingManager
from CoreApps.services.models import Service

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