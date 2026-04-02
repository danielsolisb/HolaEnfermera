from django.urls import path
from . import views

app_name = 'crm_marketing'

urlpatterns = [
    path('contactos/', views.CrmContactListView.as_view(), name='contact_list'),
    path('contactos/<int:pk>/', views.CrmContactDetailView.as_view(), name='contact_detail'),
    path('contactos/<int:pk>/editar/', views.CrmContactUpdateView.as_view(), name='contact_edit'),
    path('contactos/bulk-tag/', views.AssignTagsBulkView.as_view(), name='bulk_add_tag'),
    path('contactos/importar/', views.ContactImportView.as_view(), name='import_data'),
    path('contactos/importar/plantilla/', views.DownloadImportTemplateView.as_view(), name='download_import_template'),
    

    # Campañas
    path('campanas/', views.CampanaListView.as_view(), name='campaign_list'),
    path('campanas/crear/', views.CampanaCreateView.as_view(), name='campaign_create'),
    path('campanas/<int:pk>/editar/', views.CampanaUpdateView.as_view(), name='campaign_edit'),
    path('campanas/<int:pk>/preview/', views.CampaignPreviewView.as_view(), name='campaign_preview'),
    path('campanas/<int:pk>/execute/', views.CampaignExecuteView.as_view(), name='campaign_execute'),
    path('campanas/<int:pk>/reporte/', views.CampaignReportView.as_view(), name='campaign_report'),
    path('campanas/<int:pk>/eliminar/', views.CampanaDeleteView.as_view(), name='campaign_delete'),
    
    # Etiquetas
    path('etiquetas/', views.EtiquetaListView.as_view(), name='etiqueta_list'),
    path('etiquetas/crear/', views.EtiquetaCreateView.as_view(), name='etiqueta_create'),
    path('etiquetas/<int:pk>/editar/', views.EtiquetaUpdateView.as_view(), name='etiqueta_edit'),
    path('etiquetas/<int:pk>/eliminar/', views.EtiquetaDeleteView.as_view(), name='etiqueta_delete'),
    
    # Pipeline / Kanban
    path('pipeline/', views.PipelineBoardView.as_view(), name='pipeline_board'),
    path('pipeline/update-stage/', views.UpdateContactStageAPIView.as_view(), name='api_update_stage'),
    path('contactos/<int:pk>/toggle-proveedor/', views.ToggleProveedorAPIView.as_view(), name='toggle_proveedor'),
    path('contactos/<int:pk>/descartar/', views.ToggleDescartadoAPIView.as_view(), name='contact_discard'),
    path('contactos/<int:pk>/eliminar/', views.CrmContactDeleteView.as_view(), name='contact_delete'),
    
    # Configuración Global y Multimedia
    path('configuracion/', views.CrmConfigUpdateView.as_view(), name='config_edit'),
    path('configuracion/multimedia/crear/', views.CrmMediaTemplateCreateView.as_view(), name='media_template_create'),
    path('configuracion/multimedia/<int:pk>/eliminar/', views.CrmMediaTemplateDeleteView.as_view(), name='media_template_delete'),
]
