from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('inbox/', views.InboxView.as_view(), name='inbox'),
    path('webhook/wasender/', views.WasenderWebhookView.as_view(), name='wasender_webhook'),
    
    # Endpoints AJAX para Frontend
    path('api/chats/', views.ChatListAPIView.as_view(), name='api_chat_list'),
    path('api/chats/<int:contacto_id>/', views.ChatHistoryAPIView.as_view(), name='api_chat_history'),
    path('api/chats/<int:contacto_id>/send/', views.ChatSendAPIView.as_view(), name='api_chat_send'),
    path('api/chats/<int:contacto_id>/clear/', views.ClearChatHistoryAPIView.as_view(), name='api_chat_clear'),
]
