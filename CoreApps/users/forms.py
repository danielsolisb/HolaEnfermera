from django import forms
from django.db import transaction
from .models import User, CustomerProfile, NurseProfile

# --- FORMULARIO BASE UNIFICADO ---
# CoreApps/users/forms.py

class BaseUserForm(forms.ModelForm):
    # Campo de contraseña explícito
    password_temp = forms.CharField(
        label="Contraseña de Acceso",
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Ingrese contraseña (Opcional: Si deja vacío, será la Cédula)',
            'autocomplete': 'new-password'
        }),
        help_text="Si crea un usuario nuevo, defina su clave aquí."
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'cedula', 'email', 'telefono', 'foto']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Juan Andrés'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Pérez López'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '13', 'placeholder': 'Ej: 0999999999'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 0987654321'}),
            'foto': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'first_name': 'Nombres Completos',
            'last_name': 'Apellidos Completos',
            'cedula': 'Identificación (Cédula/RUC)',
            'telefono': 'Teléfono Celular / WhatsApp',
            'email': 'Correo Electrónico (Usuario)',
        }

    # --- VALIDACIÓN MANUAL DE CÉDULA (CORRECCIÓN DEL ERROR 500) ---
    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        if not cedula:
            raise forms.ValidationError("La cédula es obligatoria.")
            
        # Verificar si ya existe (excluyendo al usuario actual si es edición)
        if self.instance.pk: 
            if User.objects.filter(cedula=cedula).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError(f"La cédula {cedula} ya está registrada en el sistema.")
        else:
            if User.objects.filter(cedula=cedula).exists():
                raise forms.ValidationError(f"La cédula {cedula} ya pertenece a otro usuario (posiblemente un Paciente).")
        
        return cedula

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            return email
            
        if self.instance.pk:
            if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("Este correo ya está en uso.")
        else:
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError("Este correo ya está en uso.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        if not user.pk: # Solo al crear
            pwd = self.cleaned_data.get('password_temp') or self.cleaned_data.get('cedula')
            user.set_password(pwd)
            # Usamos la cédula como username para garantizar unicidad
            user.username = self.cleaned_data.get('cedula')
        elif self.cleaned_data.get('password_temp'): 
            user.set_password(self.cleaned_data.get('password_temp'))
        
        if commit:
            user.save()
        return user

# --- FORMULARIO PACIENTES ---
class PatientForm(BaseUserForm):
    # Campos específicos del perfil
    fecha_nacimiento = forms.DateField(
        label="Fecha de Nacimiento",
        required=False, 
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    ciudad = forms.CharField(
        label="Ciudad de Residencia",
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Guayaquil'})
    )
    direccion = forms.CharField(
        label="Dirección Domiciliaria (Escrita)",
        required=False, 
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Calle, número, intersección...'})
    )
    # --- CAMPO NUEVO: Google Maps ---
    google_maps_link = forms.URLField(
        label="Enlace de Google Maps (Ubicación GPS)",
        required=False,
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://maps.google.com/...'}),
        help_text="Pegue aquí el link de ubicación exacta."
    )
    alergias = forms.CharField(
        label="Alergias y Observaciones Médicas",
        required=False, 
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Indique alergias a medicamentos o condiciones especiales.'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and hasattr(self.instance, 'perfil_cliente'):
            perfil = self.instance.perfil_cliente
            self.fields['fecha_nacimiento'].initial = perfil.fecha_nacimiento
            self.fields['ciudad'].initial = perfil.ciudad
            self.fields['direccion'].initial = perfil.direccion
            self.fields['google_maps_link'].initial = perfil.google_maps_link # Cargar link existente
            self.fields['alergias'].initial = perfil.alergias

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.rol = User.Roles.CLIENTE
        if commit:
            user.save()
            perfil, _ = CustomerProfile.objects.get_or_create(user=user)
            perfil.fecha_nacimiento = self.cleaned_data['fecha_nacimiento']
            perfil.ciudad = self.cleaned_data['ciudad']
            perfil.direccion = self.cleaned_data['direccion']
            perfil.google_maps_link = self.cleaned_data['google_maps_link'] # Guardar link
            perfil.alergias = self.cleaned_data['alergias']
            perfil.save()
        return user

# --- FORMULARIO ENFERMEROS ---
class NurseForm(BaseUserForm):
    registro_profesional = forms.CharField(label="Registro SENESCYT/MSP", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    zona_cobertura = forms.CharField(label="Zona de Cobertura", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    es_motorizado = forms.BooleanField(required=False, label="¿Tiene Transporte Propio?", widget=forms.CheckboxInput(attrs={'class': 'magic-checkbox'}))
    activo_para_asignacion = forms.BooleanField(required=False, initial=True, label="Disponible para Asignación", widget=forms.CheckboxInput(attrs={'class': 'magic-checkbox'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and hasattr(self.instance, 'perfil_enfermero'):
            perfil = self.instance.perfil_enfermero
            self.fields['registro_profesional'].initial = perfil.registro_profesional
            self.fields['zona_cobertura'].initial = perfil.zona_cobertura
            self.fields['es_motorizado'].initial = perfil.es_motorizado
            self.fields['activo_para_asignacion'].initial = perfil.activo_para_asignacion

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.rol = User.Roles.ENFERMERO
        if commit:
            user.save()
            perfil, _ = NurseProfile.objects.get_or_create(user=user)
            perfil.registro_profesional = self.cleaned_data['registro_profesional']
            perfil.zona_cobertura = self.cleaned_data['zona_cobertura']
            perfil.es_motorizado = self.cleaned_data['es_motorizado']
            perfil.activo_para_asignacion = self.cleaned_data['activo_para_asignacion']
            perfil.save()
        return user