from django.shortcuts import render
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.views import View
from django.contrib.auth import get_user_model

from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
import json
from .models import User, CustomerProfile

from django.views.generic import ListView, CreateView, UpdateView

from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .forms import PatientForm, NurseForm

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


#Api para crear pacientes desde modales (AJAX) en recordatorios
@method_decorator(login_required, name='dispatch')
class QuickCreatePatientView(View):
    """
    API interna para crear pacientes desde modales (AJAX).
    """
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            # 1. Recolección de Datos
            cedula = data.get('cedula')
            email = data.get('email')
            nombres = data.get('nombres')
            apellidos = data.get('apellidos')
            telefono = data.get('telefono')
            ciudad = data.get('ciudad')

            # 2. Validaciones Previas
            if User.objects.filter(cedula=cedula).exists():
                return JsonResponse({'status': 'error', 'message': f'La cédula {cedula} ya está registrada.'}, status=400)
            
            if User.objects.filter(email=email).exists():
                return JsonResponse({'status': 'error', 'message': f'El correo {email} ya está registrado.'}, status=400)

            # 3. Creación Transaccional
            with transaction.atomic():
                # CAMBIO: Usamos la CÉDULA como username para garantizar unicidad absoluta
                # Esto evita el error 500 por duplicidad de username
                username = cedula 
                
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=cedula, # Password temporal = Cédula
                    first_name=nombres,
                    last_name=apellidos,
                    cedula=cedula,
                    telefono=telefono,
                    rol=User.Roles.CLIENTE
                )
                
                # Crear perfil
                CustomerProfile.objects.create(user=user, ciudad=ciudad)

            # 4. Retorno Exitoso
            return JsonResponse({
                'status': 'success',
                'id': user.id,
                'text': f"{user.get_full_name()} ({user.cedula})"
            })

        except IntegrityError as e:
            # Captura errores de base de datos (ej: duplicados no detectados)
            print(f"Error de Integridad: {e}")
            return JsonResponse({'status': 'error', 'message': 'Error de base de datos: Usuario duplicado.'}, status=500)
            
        except Exception as e:
            # Captura cualquier otro error y lo imprime en la consola
            print(f"❌ ERROR CRÍTICO AL CREAR PACIENTE: {str(e)}")
            import traceback
            traceback.print_exc() # Esto imprimirá el error real en tu consola negra
            return JsonResponse({'status': 'error', 'message': f'Error interno: {str(e)}'}, status=500)


# --- MIXIN DE SEGURIDAD ---
class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.rol in ['ADMINISTRADOR', 'SUPERADMIN', 'SUPERVISOR']

# ==========================
# GESTIÓN DE PACIENTES
# ==========================
class PatientListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = User
    template_name = 'users/admin/patient_list.html'
    context_object_name = 'pacientes'
    paginate_by = 20

    def get_queryset(self):
        return User.objects.filter(rol='CLIENTE').order_by('-date_joined')

class PatientCreateView(LoginRequiredMixin, AdminRequiredMixin, SuccessMessageMixin, CreateView):
    model = User
    form_class = PatientForm
    template_name = 'users/admin/patient_form.html'
    success_url = reverse_lazy('admin_patient_list')
    success_message = "Paciente creado correctamente"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Paciente'
        return context

class PatientUpdateView(LoginRequiredMixin, AdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = PatientForm
    template_name = 'users/admin/patient_form.html'
    success_url = reverse_lazy('admin_patient_list')
    success_message = "Paciente actualizado correctamente"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Editar: {self.object.get_full_name()}'
        return context

# ==========================
# GESTIÓN DE ENFERMEROS
# ==========================
class NurseListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = User
    template_name = 'users/admin/nurse_list.html'
    context_object_name = 'enfermeros'
    paginate_by = 20

    def get_queryset(self):
        return User.objects.filter(rol='ENFERMERO').order_by('first_name')

class NurseCreateView(LoginRequiredMixin, AdminRequiredMixin, SuccessMessageMixin, CreateView):
    model = User
    form_class = NurseForm
    template_name = 'users/admin/nurse_form.html'
    success_url = reverse_lazy('admin_nurse_list')
    success_message = "Enfermero registrado correctamente"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Enfermero'
        return context

class NurseUpdateView(LoginRequiredMixin, AdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = NurseForm
    template_name = 'users/admin/nurse_form.html'
    success_url = reverse_lazy('admin_nurse_list')
    success_message = "Datos del enfermero actualizados"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Editar: {self.object.get_full_name()}'
        return context