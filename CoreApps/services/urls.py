from django.urls import path
from .views import (
    ServiceListView, ServiceCreateView, ServiceUpdateView,
    MedicationListView, MedicationCreateView, MedicationUpdateView, CategoryListView, CategoryCreateView, CategoryUpdateView, CategoryDeleteView,
    ServiceDeleteView, MedicationDeleteView
)

urlpatterns = [

    # CATEGORÍAS (NUEVO)
    path('dashboard/categorias/', CategoryListView.as_view(), name='admin_category_list'),
    path('dashboard/categorias/nueva/', CategoryCreateView.as_view(), name='admin_category_create'),
    path('dashboard/categorias/editar/<int:pk>/', CategoryUpdateView.as_view(), name='admin_category_update'),
    path('dashboard/categorias/eliminar/<int:pk>/', CategoryDeleteView.as_view(), name='admin_category_delete'),

    # SERVICIOS
    path('dashboard/servicios/', ServiceListView.as_view(), name='admin_service_list'),
    path('dashboard/servicios/nuevo/', ServiceCreateView.as_view(), name='admin_service_create'),
    path('dashboard/servicios/editar/<int:pk>/', ServiceUpdateView.as_view(), name='admin_service_update'),
    path('dashboard/servicios/eliminar/<int:pk>/', ServiceDeleteView.as_view(), name='admin_service_delete'),

    # MEDICAMENTOS
    path('dashboard/medicamentos/', MedicationListView.as_view(), name='admin_medication_list'),
    path('dashboard/medicamentos/nuevo/', MedicationCreateView.as_view(), name='admin_medication_create'),
    path('dashboard/medicamentos/editar/<int:pk>/', MedicationUpdateView.as_view(), name='admin_medication_update'),
    path('dashboard/medicamentos/eliminar/<int:pk>/', MedicationDeleteView.as_view(), name='admin_medication_delete'),
]