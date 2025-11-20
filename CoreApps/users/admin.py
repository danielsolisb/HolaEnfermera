from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, CustomerProfile, NurseProfile

class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    can_delete = False
    verbose_name_plural = 'Perfil de Cliente'

class NurseProfileInline(admin.StackedInline):
    model = NurseProfile
    can_delete = False
    verbose_name_plural = 'Perfil de Enfermero'

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('email', 'first_name', 'last_name', 'rol', 'is_staff')
    list_filter = ('rol', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Información Extra', {'fields': ('rol', 'cedula', 'telefono', 'foto')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información Extra', {'fields': ('rol', 'cedula', 'telefono', 'foto')}),
    )
    
    def get_inlines(self, request, obj=None):
        """Muestra el perfil correspondiente según el rol seleccionado"""
        if not obj:
            return []
        if obj.rol == User.Roles.CLIENTE:
            return [CustomerProfileInline]
        if obj.rol == User.Roles.ENFERMERO:
            return [NurseProfileInline]
        return []

admin.site.register(User, CustomUserAdmin)