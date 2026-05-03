from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, DeanProfile, Department, FacultyProfile, School, StudentProfile


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'username', 'first_name', 'last_name', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    fieldsets = UserAdmin.fieldsets + (('SaiU OD Role', {'fields': ('role', 'mobile', 'must_change_password')}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('SaiU OD Role', {'fields': ('email', 'role', 'mobile')}),)


admin.site.register(School)
admin.site.register(Department)
admin.site.register(StudentProfile)
admin.site.register(FacultyProfile)
admin.site.register(DeanProfile)
