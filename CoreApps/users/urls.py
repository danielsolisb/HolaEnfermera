from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import CustomLoginView

urlpatterns = [
    # La ruta es vacía aquí porque la incluiremos con el prefijo 'login/' en el config principal, 
    # O podemos definirla explícitamente aquí. 
    # Para cumplir tu requisito de "localhost:8000/login":
    
    path('login/', CustomLoginView.as_view(), name='login'),
    
    # Aprovechamos para dejar listo el logout
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
]