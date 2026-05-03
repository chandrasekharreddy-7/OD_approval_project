from django.contrib import admin
from .models import AuditLog, LoginAttempt
admin.site.register(AuditLog)
admin.site.register(LoginAttempt)
