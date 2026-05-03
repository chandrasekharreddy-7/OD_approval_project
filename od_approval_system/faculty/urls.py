from django.urls import path
from . import views

app_name = 'faculty'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('requests/', views.pending_requests, name='pending_requests'),
    path('requests/<int:pk>/', views.request_detail, name='request_detail'),
    path('requests/<int:pk>/approve/', views.approve_request, name='approve_request'),
    path('requests/<int:pk>/reject/', views.reject_request, name='reject_request'),
    path('students/<int:student_id>/history/', views.student_history, name='student_history'),
    path('students/upload/', views.upload_students, name='upload_students'),
]
