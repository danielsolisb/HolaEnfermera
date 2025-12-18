from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics, permissions, filters
from .serializers import (
    MyTokenObtainPairSerializer, 
    UserProfileSerializer,
    PatientCreateSerializer,
    NurseCreateSerializer
)
from django.contrib.auth import get_user_model

User = get_user_model()

class MyTokenObtainPairView(TokenObtainPairView):
    """
    Login personalizado que valida si el usuario es ADMINISTRADOR.
    """
    serializer_class = MyTokenObtainPairSerializer

class UserProfileView(generics.RetrieveAPIView):
    """
    Devuelve los datos del usuario logueado.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

# --- VISTAS DE LECTURA (LISTADOS) ---

class PatientListAPIView(generics.ListAPIView):
    """
    Lista de Pacientes (Clientes).
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['first_name', 'last_name', 'cedula', 'email']

    def get_queryset(self):
        return User.objects.filter(rol=User.Roles.CLIENTE).order_by('-date_joined')

class NurseListAPIView(generics.ListAPIView):
    """
    Lista de Enfermeros.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['first_name', 'last_name', 'cedula', 'email']

    def get_queryset(self):
        return User.objects.filter(rol=User.Roles.ENFERMERO).order_by('first_name')

# --- VISTAS DE CREACIÓN ---

class PatientCreateAPIView(generics.CreateAPIView):
    """
    Endpoint para registrar Pacientes.
    Requiere ser Admin/Staff autenticado.
    """
    queryset = User.objects.all()
    serializer_class = PatientCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

class NurseCreateAPIView(generics.CreateAPIView):
    """
    Endpoint para registrar Enfermeros.
    Requiere ser Admin/Staff autenticado.
    """
    queryset = User.objects.all()
    serializer_class = NurseCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
