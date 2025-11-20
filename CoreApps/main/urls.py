from django.urls import path
from .views import LandingView, DashboardView

urlpatterns = [
    path('', LandingView.as_view(), name='home'),         # La raíz localhost:8000/
    path('dashboard/', DashboardView.as_view(), name='dashboard'), # localhost:8000/dashboard/
]