from rest_framework import serializers
from CoreApps.services.models import Service, Medication, ServiceCategory

class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ['id', 'nombre', 'icono']

class ServiceSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.ReadOnlyField(source='categoria.nombre')
    
    class Meta:
        model = Service
        fields = '__all__'

class MedicationSerializer(serializers.ModelSerializer):
    # Campos explicativos para la App móvil
    frecuencia_unidad_display = serializers.CharField(source='get_frecuencia_unidad_display', read_only=True)
    
    class Meta:
        model = Medication
        fields = '__all__'
