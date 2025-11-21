from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

class LandingView(TemplateView):
    """Página pública (Usa el base.html de Tailwind)"""
    template_name = 'main/index.html'

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Panel Principal (Usa dashboard_base.html de Nifty).
    Accesible para Administradores, Supervisores y Enfermeros.
    """
    template_name = 'main/dashboard/index.html'

    def dispatch(self, request, *args, **kwargs):
        # Validación extra de seguridad: Si es 'CLIENTE', no debería ver el dashboard interno
        if request.user.is_authenticated and request.user.rol == 'CLIENTE':
            return redirect('home') # O a un perfil de cliente simple
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Aquí pasaremos estadísticas reales luego (Citas de hoy, Ingresos, etc.)
        context['titulo_panel'] = "Resumen Operativo"
        return context