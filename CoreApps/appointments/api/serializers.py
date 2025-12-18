from rest_framework import serializers
from CoreApps.appointments.models import AppointmentReminder
from CoreApps.services.models import Service, Medication
from django.contrib.auth import get_user_model

User = get_user_model()

# --- Nested Serializers (Solo Lectura) ---

class SimpleUserSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(source='get_full_name')
    class Meta:
        model = User
        fields = ['id', 'email', 'fullname', 'cedula', 'telefono', 'foto']

class SimpleServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'nombre', 'precio_base']

class SimpleMedicationSerializer(serializers.ModelSerializer):
    frecuencia_txt = serializers.CharField(source='__str__', read_only=True)
    class Meta:
        model = Medication
        fields = ['id', 'nombre', 'frecuencia_txt']

# --- Main Serializer ---

class LeadSerializer(serializers.ModelSerializer):
    paciente = SimpleUserSerializer(read_only=True)
    medicamento_catalogo = SimpleMedicationSerializer(read_only=True)
    servicio_sugerido = SimpleServiceSerializer(read_only=True)
    
    # Campos calculados o formateados
    origen_display = serializers.CharField(source='get_origen_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    class Meta:
        model = AppointmentReminder
        fields = [
            'id', 'paciente', 'medicamento_catalogo', 'servicio_sugerido', 'medicamento_externo',
            'fecha_ultima_aplicacion', 'fecha_limite_sugerida', 
            'origen', 'origen_display',
            'estado', 'estado_display',
            'notas', 'fecha_creacion'
        ]
        read_only_fields = ['fecha_creacion', 'paciente', 'origen']

    def update(self, instance, validated_data):
        # Permitimos actualizar estado y notas
        instance.estado = validated_data.get('estado', instance.estado)
        instance.notas = validated_data.get('notas', instance.notas)
        
        # Si quisieras permitir reagendar fecha:
        if 'fecha_limite_sugerida' in validated_data:
            instance.fecha_limite_sugerida = validated_data['fecha_limite_sugerida']
            
        instance.save()
        return instance
