from django import forms
from .models import Service, Medication, ServiceCategory, MedicationDoseStep
from django.forms import inlineformset_factory

# --- NUEVO: FORMULARIO DE CATEGORÍAS ---
class CategoryForm(forms.ModelForm):
    class Meta:
        model = ServiceCategory
        fields = ['nombre', 'icono']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Vacunación, Sueroterapia...'}),
            # El icono es un ImageField en tu modelo
            'icono': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'nombre': 'Nombre de la Categoría',
            'icono': 'Ícono o Imagen Representativa'
        }

# --- ACTUALIZADO: FORMULARIO DE SERVICIOS ---
class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        # AGREGAMOS 'categoria' AL INICIO
        fields = ['categoria', 'nombre', 'descripcion', 'precio_base', 'precio_insumos', 'duracion_horas', 'incluye_insumos_por_defecto', 'activo']
        widgets = {
            # Widget para el select de categoría
            'categoria': forms.Select(attrs={'class': 'form-control selectpicker', 'data-live-search': 'true'}),
            
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Vacuna contra Fiebre Amarilla'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'precio_base': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'precio_insumos': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'duracion_horas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'incluye_insumos_por_defecto': forms.CheckboxInput(attrs={'class': 'magic-checkbox'}),
            'activo': forms.CheckboxInput(attrs={'class': 'magic-checkbox'}),
        }
        labels = {
            'categoria': 'Categoría del Servicio',
            'precio_base': 'Precio del Servicio ($)',
            'precio_insumos': 'Costo de Insumos ($)',
            'duracion_horas': 'Duración (Horas)',
            'incluye_insumos_por_defecto': 'El precio base ya incluye insumos',
            'activo': 'Servicio habilitado'
        }

class MedicationForm(forms.ModelForm):
    class Meta:
        model = Medication
        fields = ['nombre', 'descripcion', 'frecuencia_valor', 'frecuencia_unidad', 'es_recurrente', 'es_secuencial', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Neurobión 3ml'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'frecuencia_valor': forms.NumberInput(attrs={'class': 'form-control'}),
            'frecuencia_unidad': forms.Select(attrs={'class': 'form-control selectpicker'}),
            'es_recurrente': forms.CheckboxInput(attrs={'class': 'magic-checkbox'}),
            'es_secuencial': forms.CheckboxInput(attrs={'class': 'magic-checkbox'}),
            'activo': forms.CheckboxInput(attrs={'class': 'magic-checkbox'}),
        }
        labels = {
            'frecuencia_valor': 'Cada cuánto tiempo se aplica',
            'frecuencia_unidad': 'Unidad de Tiempo',
            'es_recurrente': 'Activar recordatorio cíclico (de por vida)',
            'es_secuencial': 'Activar esquema de dosis secuencial (ej: vacunas)',
            'activo': 'Visible en el Buscador Público'
        }

# --- NUEVO: FORMULARIO PARA PASOS DE DOSIS ---
class MedicationDoseStepForm(forms.ModelForm):
    class Meta:
        model = MedicationDoseStep
        fields = ['numero_dosis_siguiente', 'espera_valor', 'espera_unidad']
        widgets = {
            'numero_dosis_siguiente': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 2'}),
            'espera_valor': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 6'}),
            'espera_unidad': forms.Select(attrs={'class': 'form-control selectpicker'}),
        }
        labels = {
            'numero_dosis_siguiente': 'Siguiente Dosis #',
            'espera_valor': 'Esperar...',
            'espera_unidad': 'Unidad de Tiempo',
        }

# FormSet para manejar múltiples dosis de forma dinámica
MedicationDoseStepFormSet = inlineformset_factory(
    Medication, 
    MedicationDoseStep,
    form=MedicationDoseStepForm,
    extra=1,
    can_delete=True
)