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
    # 1. Redefinimos el email para que sea opcional en el HTML
    email = forms.EmailField(
        label="Correo Electrónico",
        required=False,  # <--- CLAVE: Permite enviar vacío
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Opcional. Se generará automático si se deja vacío.'})
    )
    
    # Campos del perfil...
    fecha_nacimiento = forms.DateField(
        label="Fecha de Nacimiento",
        required=False, 
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    # ... (resto de campos igual: ciudad, direccion, google_maps, alergias) ...
    ciudad = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    direccion = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))
    google_maps_link = forms.URLField(required=False, widget=forms.URLInput(attrs={'class': 'form-control'}))
    alergias = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and hasattr(self.instance, 'perfil_cliente'):
            perfil = self.instance.perfil_cliente
            self.fields['fecha_nacimiento'].initial = perfil.fecha_nacimiento
            self.fields['ciudad'].initial = perfil.ciudad
            self.fields['direccion'].initial = perfil.direccion
            self.fields['google_maps_link'].initial = perfil.google_maps_link
            self.fields['alergias'].initial = perfil.alergias

    # 2. Lógica de Auto-Generación (Backend Puro)
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        cedula = cleaned_data.get('cedula')

        # Si no hay email pero hay cédula, generamos el ficticio
        if not email and cedula:
            # FORMATO: 0991234567@holaenfermera.com
            dummy_email = f"{cedula}@holaenfermera.com"
            
            # Inyectamos el valor generado para que el resto del sistema lo use
            cleaned_data['email'] = dummy_email
            
            # (Opcional) Podríamos verificar unicidad aquí, pero clean_cedula ya garantiza
            # que la cédula es única, por ende el email derivado también lo será.
        
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        # El user.email ya vendrá lleno desde clean()
        user = super().save(commit=False)
        user.rol = User.Roles.CLIENTE
        
        # Aseguramos que el email se asigne (por si clean no corrió en algún contexto extraño)
        if not user.email and user.cedula:
            user.email = f"{user.cedula}@holaenfermera.com"

        if commit:
            user.save()
            perfil, _ = CustomerProfile.objects.get_or_create(user=user)
            perfil.fecha_nacimiento = self.cleaned_data.get('fecha_nacimiento')
            perfil.ciudad = self.cleaned_data.get('ciudad')
            perfil.direccion = self.cleaned_data.get('direccion')
            perfil.google_maps_link = self.cleaned_data.get('google_maps_link')
            perfil.alergias = self.cleaned_data.get('alergias')
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