from django.urls import path
from . import views

app_name = 'dean'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('requests/', views.approval_requests, name='approval_requests'),
    path('requests/<int:pk>/', views.request_detail, name='request_detail'),
    path('requests/<int:pk>/approve/', views.approve_request, name='approve_request'),
    path('requests/<int:pk>/reject/', views.reject_request, name='reject_request'),
    path('rules/', views.rules, name='rules'),
    path('faculty/', views.manage_faculty, name='manage_faculty'),
    path('faculty/add/', views.add_faculty, name='add_faculty'),
    path('faculty/<int:user_id>/transfer/', views.transfer_faculty, name='transfer_faculty'),
    path('faculty/<int:user_id>/delete/', views.delete_faculty, name='delete_faculty'),
    path('students/', views.manage_students, name='manage_students'),
    path('students/<int:student_id>/transfer/', views.transfer_student, name='transfer_student'),
    path('students/upload/', views.upload_students, name='upload_students'),
]
