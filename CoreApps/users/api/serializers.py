from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from CoreApps.users.models import CustomerProfile, NurseProfile

User = get_user_model()

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Añadir claims personalizados
        token['rol'] = user.rol
        token['email'] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        
        # VALIDACIÓN DE ROL: Solo Admins
        if self.user.rol not in ['ADMINISTRADOR', 'SUPERADMIN', 'SUPERVISOR'] and not self.user.is_superuser:
            raise serializers.ValidationError(
                {"detail": "No tienes permisos de administrador para acceder a esta App."}
            )
            
        return data

class UserProfileSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(source='get_full_name')
    
    class Meta:
        model = User
        fields = ['id', 'email', 'fullname', 'rol', 'foto', 'cedula', 'telefono']

# --- NUEVOS SERIALIZERS PARA CREACIÓN ---

class PatientCreateSerializer(serializers.ModelSerializer):
    # Campos del Perfil de Cliente
    direccion = serializers.CharField(write_only=True, required=False, allow_blank=True)
    ciudad = serializers.CharField(write_only=True, required=False, allow_blank=True)
    alergias = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    # Geolocalización
    lat = serializers.DecimalField(max_digits=15, decimal_places=10, write_only=True, required=False)
    lng = serializers.DecimalField(max_digits=15, decimal_places=10, write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'cedula', 'telefono', 'email', 
            'direccion', 'ciudad', 'alergias', 'lat', 'lng'
        ]
        extra_kwargs = {
            'email': {'required': False}, # Opcional, lo autogeneramos si falta
            'cedula': {'required': True}
        }

    def validate_cedula(self, value):
        if User.objects.filter(cedula=value).exists():
            raise serializers.ValidationError("Esta cédula ya está registrada.")
        return value

    def create(self, validated_data):
        # Separar datos del perfil
        profile_data = {
            'direccion': validated_data.pop('direccion', ''),
            'ciudad': validated_data.pop('ciudad', ''),
            'alergias': validated_data.pop('alergias', ''),
            'ubicacion_gps_lat': validated_data.pop('lat', None),
            'ubicacion_gps_lng': validated_data.pop('lng', None),
        }

        # Lógica de Email ficticio
        cedula = validated_data.get('cedula')
        email = validated_data.get('email')
        if not email:
            email = f"{cedula}@holaenfermera.com"
            validated_data['email'] = email
        
        # El username será la cédula (o email, según prefieras, pero user.create_user pide username)
        username = cedula
        password = cedula # Contraseña por defecto = cédula
        
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                password=password,
                rol=User.Roles.CLIENTE,
                **validated_data
            )
            
            # Crear Perfil
            CustomerProfile.objects.create(user=user, **profile_data)
            
        return user

class NurseCreateSerializer(serializers.ModelSerializer):
    # Campos del Perfil Enfermero
    registro_profesional = serializers.CharField(write_only=True, required=False, allow_blank=True)
    es_motorizado = serializers.BooleanField(write_only=True, default=False)
    zona_cobertura = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'cedula', 'telefono', 'email',
            'registro_profesional', 'es_motorizado', 'zona_cobertura'
        ]
        extra_kwargs = {
            'email': {'required': True}, # Enfermeros sí deben tener email real
            'cedula': {'required': True}
        }

    def create(self, validated_data):
        profile_data = {
            'registro_profesional': validated_data.pop('registro_profesional', ''),
            'es_motorizado': validated_data.pop('es_motorizado', False),
            'zona_cobertura': validated_data.pop('zona_cobertura', ''),
        }

        cedula = validated_data.get('cedula')
        username = cedula
        password = cedula 
        
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                password=password,
                rol=User.Roles.ENFERMERO,
                **validated_data
            )
            
            NurseProfile.objects.create(user=user, **profile_data)
            
        return user
