from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('ask/', views.chat, name='ask'),
]
