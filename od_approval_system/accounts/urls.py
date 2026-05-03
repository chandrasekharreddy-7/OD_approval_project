from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_student, name='register_student'),
    path('redirect/', views.role_redirect, name='redirect'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.password_change_required, name='password_change_required'),
]
