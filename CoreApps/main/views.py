from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class LandingView(TemplateView):
    """Página pública inicial (Landing Page)"""
    template_name = 'main/index.html'

class DashboardView(LoginRequiredMixin, TemplateView):
    """Panel principal (Solo usuarios logueados)"""
    template_name = 'main/dashboard/main_dashboard.html' # Ajusta a tu estructura