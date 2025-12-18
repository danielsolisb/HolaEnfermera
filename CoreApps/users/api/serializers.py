from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model

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
