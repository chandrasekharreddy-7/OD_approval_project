from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('apply/', views.apply_od, name='apply_od'),
    path('requests/', views.my_requests, name='my_requests'),
    path('requests/<int:pk>/', views.request_detail, name='request_detail'),
    path('requests/<int:pk>/cancel/', views.cancel_request, name='cancel_request'),
    path('requests/<int:pk>/pdf/', views.download_od_pdf, name='download_od_pdf'),
]
