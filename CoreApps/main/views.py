from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

class LandingView(TemplateView):
    """Página pública (Usa el base.html de Tailwind)"""
    template_name = 'main/index.html'

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Vista Dispatcher: Redirige al template correcto según el rol.
    """
    def get_template_names(self):
        user = self.request.user
        
        # 1. ADMINISTRADORES (Admin, SuperAdmin, Supervisor)
        if user.rol in ['ADMINISTRADOR', 'SUPERADMIN', 'SUPERVISOR'] or user.is_superuser:
            return ['main/dashboard/admin_home.html']
        
        # 2. ENFERMEROS
        elif user.rol == 'ENFERMERO':
            return ['main/dashboard/nurse_home.html']
        
        # 3. CLIENTES (Por defecto)
        else:
            return ['main/dashboard/client_home.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user_role'] = user.rol
        
        # LOGICA PARA ADMIN DASHBOARD
        if user.rol in ['ADMINISTRADOR', 'SUPERADMIN', 'SUPERVISOR'] or user.is_superuser:
            from django.contrib.auth import get_user_model
            from CoreApps.appointments.models import AppointmentReminder
            from CoreApps.notifications.models import NotificationLog
            from django.utils import timezone
            from datetime import timedelta
            from django.db import models
            
            User = get_user_model()
            ahora = timezone.now()
            hace_24h = ahora - timedelta(hours=24)
            
            # 1. KPIs Principales
            context['total_pacientes'] = User.objects.filter(rol='CLIENTE').count()
            
            # Pendientes "Operativos" (Vencidos o Futuros que están pendientes)
            context['total_pendientes'] = AppointmentReminder.objects.filter(
                estado='PENDIENTE'
            ).count()
            
            context['total_leads_web'] = AppointmentReminder.objects.filter(
                origen='WEB', 
                estado='PENDIENTE'
            ).count()
            
            # 2. Worker Stats (Últimas 24 horas)
            context['worker_enviados_24h'] = NotificationLog.objects.filter(
                fecha_intento__gte=hace_24h,
                enviado=True
            ).count()
            
            # 3. Listados Rápidos
            context['ultimos_logs'] = NotificationLog.objects.select_related('recordatorio__paciente').order_by('-fecha_intento')[:5]

            # 4. Top Enfermeros (Por Citas Asignadas)
            # Asegúrate que el modelo Appointment tiene related_name='citas_asignadas' en el campo enfermero
            context['top_nurses'] = User.objects.filter(rol='ENFERMERO') \
                .annotate(total_citas=models.Count('citas_asignadas')) \
                .order_by('-total_citas')[:5]

            # 5. Datos para Gráficos
            # Embudo de Estados
            c_pendiente = AppointmentReminder.objects.filter(estado='PENDIENTE').count()
            c_contactado = AppointmentReminder.objects.filter(estado='CONTACTADO').count()
            c_agendado = AppointmentReminder.objects.filter(estado='AGENDADO').count()
            c_expirado = AppointmentReminder.objects.filter(estado='EXPIRADO').count()
            
            # Formato simple para JS: [P, C, A, E]
            context['chart_status_data'] = [c_pendiente, c_contactado, c_agendado, c_expirado]
            
        return context


