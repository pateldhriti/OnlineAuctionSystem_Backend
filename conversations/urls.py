from django.urls import path

from . import views

app_name = 'conversations'

urlpatterns = [
    path('', views.conversation_list, name='list'),
    path('<int:pk>/', views.conversation_detail, name='detail'),
    path('<int:pk>/send/', views.send_message, name='send'),
]
