"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    # 1. Rutas de Usuarios (Login/Logout)
    # Al usar path('', ...), las rutas internas 'login/' se pegan a la raíz -> /login/
    path('', include('CoreApps.users.urls')),
    
    # 2. Rutas Principales (Home, Dashboard)
    # También las pegamos a la raíz.
    # 'main.urls' contiene el path('', ...) que atrapará la raíz si nadie más lo hizo antes.
    path('', include('CoreApps.main.urls')),
    # Esto hace que las rutas queden como: 
    # localhost:8000/citas/api/availability/
    path('citas/', include('CoreApps.appointments.urls')),
    path('', include('CoreApps.services.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Agrega también esta línea para asegurar que busque en STATICFILES_DIRS si STATIC_ROOT está vacío
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)