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
        1. Si es Superuser (Root) -> Va al Admin de Django.
        2. Si es otro usuario -> Va a la página principal (Dashboard o Landing).
        """
        user = self.request.user
        
        if user.is_superuser:
            return '/admin/'  # Redirección directa al portal administrativo
            
        # Aquí definiremos a dónde van los enfermeros/clientes. 
        # Por ahora los mandamos a una ruta llamada 'home' (la crearemos luego).
        return reverse_lazy('home') 

    def form_invalid(self, form):
        messages.error(self.request, "Usuario o contraseña incorrectos.")
        return super().form_invalid(form)