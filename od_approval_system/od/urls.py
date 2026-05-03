from django.urls import path
from . import views

app_name = 'od'

urlpatterns = [
    path('verify/<uuid:verification_id>/', views.verify_od, name='verify'),
    path('documents/<int:document_id>/', views.download_document, name='download_document'),
]
