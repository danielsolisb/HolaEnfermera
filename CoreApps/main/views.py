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
        context['user_role'] = self.request.user.rol
        return context


