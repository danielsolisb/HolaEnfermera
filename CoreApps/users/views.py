from django.shortcuts import render
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib import messages

class CustomLoginView(LoginView):
    template_name = 'login/login.html'
    redirect_authenticated_user = True # Si ya está logueado, no le muestra el login

    def get_success_url(self):
        """
        Lógica de redirección post-login:
        1. Superuser -> Admin de Django
        2. Staff (Admin/Supervisor/Enfermero) -> Dashboard (Nifty)
        3. Cliente -> Home (Landing Page)
        """
        user = self.request.user
        
        # Si es Superusuario (Root), al admin técnico
        if user.is_superuser:
            return '/admin/'
            
        # Si es Staff o tiene rol de gestión, al Dashboard
        if user.is_staff or user.rol in ['ADMINISTRADOR', 'SUPERVISOR', 'ENFERMERO']:
            return reverse_lazy('dashboard')
            
        # Si es cliente normal, a la página principal
        return reverse_lazy('home')
    def form_invalid(self, form):
        messages.error(self.request, "Usuario o contraseña incorrectos.")
        return super().form_invalid(form)