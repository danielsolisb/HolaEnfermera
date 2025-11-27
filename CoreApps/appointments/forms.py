from django import forms
from django.utils import timezone
from .models import AppointmentReminder
from CoreApps.users.models import User

class AppointmentReminderForm(forms.ModelForm):
    # Campo auxiliar (no se guarda en BD, solo ayuda a calcular)
    fecha_aplicacion = forms.DateField(
        label="Fecha de Aplicación",
        required=False,
        initial=timezone.now().date(),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    class Meta:
        model = AppointmentReminder
        fields = ['paciente', 'medicamento_catalogo', 'medicamento_externo', 'fecha_limite_sugerida', 'notas', 'estado']
        widgets = {
            # Agregamos 'readonly' por defecto a la sugerida, JS la controlará
            'fecha_limite_sugerida': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'medicamento_externo': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control selectpicker'}),
            'paciente': forms.Select(attrs={'class': 'form-control selectpicker', 'data-live-search': 'true'}),
            'medicamento_catalogo': forms.Select(attrs={'class': 'form-control selectpicker', 'data-live-search': 'true'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['paciente'].queryset = User.objects.filter(rol='CLIENTE')
        
        # Ordenamos la fecha sugerida al final para que visualmente quede mejor
        self.fields['fecha_limite_sugerida'].label = "Fecha Próxima Dosis (Calculada)"