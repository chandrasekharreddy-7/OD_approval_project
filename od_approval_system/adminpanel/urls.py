from django.urls import path
from . import views

app_name = 'adminpanel'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('students/', views.manage_students, name='manage_students'),
    path('students/<int:student_id>/transfer/', views.transfer_student, name='transfer_student'),
    path('users/', views.manage_users, name='manage_users'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/<int:user_id>/toggle/', views.deactivate_user, name='deactivate_user'),
    path('users/<int:user_id>/reset-password/', views.reset_password, name='reset_password'),
    path('deans/', views.manage_deans, name='manage_deans'),
    path('deans/add/', views.add_dean, name='add_dean'),
    path('deans/<int:user_id>/transfer/', views.transfer_dean, name='transfer_dean'),
    path('deans/<int:user_id>/delete/', views.delete_dean, name='delete_dean'),
    path('faculty/', views.manage_faculty, name='manage_faculty'),
    path('faculty/<int:user_id>/transfer/', views.transfer_faculty, name='transfer_faculty'),
    path('faculty/<int:user_id>/delete/', views.delete_faculty, name='delete_faculty'),
    path('schools-departments/', views.schools_departments, name='schools_departments'),
    path('categories/', views.od_categories, name='od_categories'),
    path('rules/', views.od_rules, name='od_rules'),
    path('od-requests/', views.all_od_requests, name='all_od_requests'),
    path('audit-logs/', views.audit_logs, name='audit_logs'),
    path('import-students/', views.import_students, name='import_students'),
]
