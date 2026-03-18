from django.contrib import admin
from .models import Ciudad

@admin.register(Ciudad)
class CiudadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activa')
    search_fields = ('nombre',)
    list_filter = ('activa',)
