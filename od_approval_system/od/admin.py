from django.contrib import admin
from .models import ODApproval, ODCategory, ODRequest, ODRule, UploadedDocument

admin.site.register(ODCategory)
admin.site.register(ODRule)
admin.site.register(ODRequest)
admin.site.register(ODApproval)
admin.site.register(UploadedDocument)
