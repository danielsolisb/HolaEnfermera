from django.contrib.auth.models import AbstractUser, Group, Permission # <--- Importa Group y Permission
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

class User(AbstractUser):
    """
    Modelo base para TODOS los actores (Clientes, Enfermeros, Admin).
    """
    class Roles(models.TextChoices):
        CLIENTE = 'CLIENTE', _('Cliente')
        ENFERMERO = 'ENFERMERO', _('Enfermero')
        SUPERVISOR = 'SUPERVISOR', _('Supervisor')
        ADMINISTRADOR = 'ADMINISTRADOR', _('Administrador')
        SUPERADMIN = 'SUPERADMIN', _('Super Administrador')

    email = models.EmailField(_('Correo Electrónico'), unique=True)
    # username = ... (lo hereda de AbstractUser, déjalo o ponlo blank=True si prefieres)

    # --- INICIO DE LA SOLUCIÓN AL ERROR ---
    # Sobrescribimos estos campos para evitar el conflicto con auth.User
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        help_text=_('The groups this user belongs to.'),
        related_name="custom_user_groups",  # Nombre único para evitar el choque
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="custom_user_permissions", # Nombre único para evitar el choque
        related_query_name="user",
    )
    # --- FIN DE LA SOLUCIÓN ---

    rol = models.CharField(
        max_length=20, 
        choices=Roles.choices, 
        default=Roles.CLIENTE,
        verbose_name=_('Rol en el sistema')
    )
    cedula = models.CharField(
        _('Cédula / RUC'), 
        max_length=13, 
        unique=True, 
        blank=True, 
        null=True
    )
    telefono = models.CharField(
        _('Teléfono Celular'), 
        max_length=20, 
        blank=True, 
        null=True,
        help_text=_('Número principal para contacto')
    )
    foto = models.ImageField(upload_to='perfiles/fotos/', blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'cedula']

    class Meta:
        verbose_name = _('Usuario')
        verbose_name_plural = _('Usuarios')

    def __str__(self):
        return f"{self.get_full_name()} ({self.rol})"

    def save(self, *args, **kwargs):
        if self.rol in [self.Roles.ADMINISTRADOR, self.Roles.SUPERADMIN, self.Roles.SUPERVISOR]:
            self.is_staff = True
        if self.rol == self.Roles.SUPERADMIN:
            self.is_superuser = True
        super().save(*args, **kwargs)



class CustomerProfile(models.Model):
    """
    Perfil exclusivo para pacientes/clientes.
    Datos: Ubicación, Nacimiento, Historial Médico básico.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='perfil_cliente'
    )
    fecha_nacimiento = models.DateField(_('Fecha de Nacimiento'), null=True, blank=True)
    ciudad = models.CharField(_('Ciudad'), max_length=100, blank=True)
    direccion = models.TextField(_('Dirección Domiciliaria'), blank=True)
    referencia_ubicacion = models.TextField(_('Referencia de Ubicación'), blank=True, null=True)
    
    # Geolocalización (Google Maps)
    ubicacion_gps_lat = models.DecimalField(
        _('Latitud'), max_digits=15, decimal_places=10, null=True, blank=True
    )
    ubicacion_gps_lng = models.DecimalField(
        _('Longitud'), max_digits=15, decimal_places=10, null=True, blank=True
    )
    
    google_maps_link = models.URLField(_('Link Google Maps'), max_length=500, blank=True, null=True)

    # Datos médicos básicos para el servicio
    alergias = models.TextField(_('Alergias conocidas'), blank=True)
    observaciones_medicas = models.TextField(_('Observaciones Médicas'), blank=True)

    def __str__(self):
        return f"Perfil Cliente: {self.user.email}"
    def save(self, *args, **kwargs):
        # Generar Link Automáticamente si hay coordenadas y no hay link
        if self.ubicacion_gps_lat and self.ubicacion_gps_lng and not self.google_maps_link:
            self.google_maps_link = f"https://www.google.com/maps/search/?api=1&query={self.ubicacion_gps_lat},{self.ubicacion_gps_lng}"
        super().save(*args, **kwargs)

class NurseProfile(models.Model):
    """
    Perfil exclusivo para enfermeros.
    Datos: Profesionales, Logística, Cobertura.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='perfil_enfermero'
    )
    registro_profesional = models.CharField(
        _('Registro SENESCYT/MSP'), 
        max_length=50, 
        blank=True
    )
    es_motorizado = models.BooleanField(
        _('Tiene transporte propio (Moto/Auto)'), 
        default=False
    )
    zona_cobertura = models.CharField(
        _('Zona de Cobertura'), 
        max_length=100, 
        blank=True,
        help_text=_('Ej: Norte, Sur, Samborondón')
    )
    activo_para_asignacion = models.BooleanField(
        _('Disponible para recibir citas'), 
        default=True
    )

    def __str__(self):
        return f"Perfil Enfermero: {self.user.get_full_name()}"