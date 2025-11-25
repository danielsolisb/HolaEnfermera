from django.shortcuts import render
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.views import View
from django.contrib.auth import get_user_model

User = get_user_model()

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

class PublicNurseListAPIView(View):
    """
    API Pública: Retorna lista de enfermeros para el selector del formulario.
    Devuelve: ID, Nombre Completo y URL de Foto.
    """
    def get(self, request):
        # Filtramos solo enfermeros activos
        enfermeros = User.objects.filter(rol='ENFERMERO', is_active=True)
        
        data = []
        for enf in enfermeros:
            data.append({
                'id': enf.id,
                'nombre': f"{enf.first_name} {enf.last_name}",
                'foto': enf.foto.url if enf.foto else None # Asegúrate que el modelo User tenga 'foto'
            })
            
        return JsonResponse({'status': 'success', 'enfermeros': data})