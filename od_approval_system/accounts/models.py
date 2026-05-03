from django.conf import settings
import os
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    STUDENT = 'STUDENT', 'Student'
    FACULTY = 'FACULTY', 'Faculty/Mentor'
    DEAN = 'DEAN', 'Dean'
    ADMIN = 'ADMIN', 'Admin'



def secure_signature_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    role = getattr(getattr(instance, 'user', None), 'role', 'staff').lower()
    return f'signatures/{role}/{uuid.uuid4().hex}{ext}'

class CustomUser(AbstractUser):
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.STUDENT)
    email = models.EmailField(unique=True)
    mobile = models.CharField(max_length=15, blank=True)
    must_change_password = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        ordering = ['first_name', 'last_name', 'email']

    def __str__(self):
        return self.get_full_name() or self.email

    @property
    def is_student(self):
        return self.role == UserRole.STUDENT

    @property
    def is_faculty(self):
        return self.role == UserRole.FACULTY

    @property
    def is_dean(self):
        return self.role == UserRole.DEAN

    @property
    def is_admin_role(self):
        return self.role == UserRole.ADMIN or self.is_superuser


class School(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    official_dean_name = models.CharField(max_length=150, blank=True)
    source_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'schools'
        ordering = ['name']

    def __str__(self):
        return self.name


class Department(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'departments'
        unique_together = ('school', 'name')
        ordering = ['school__name', 'name']

    def __str__(self):
        return f'{self.name} ({self.school.code})'


class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    roll_number = models.CharField(max_length=40, unique=True)
    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name='students')
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='students')
    year = models.PositiveSmallIntegerField(default=1)
    section = models.CharField(max_length=20)
    semester = models.PositiveSmallIntegerField(default=1)
    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='mentored_students')
    staff_uploaded_login = models.BooleanField(default=False, help_text='Students can login only after faculty/dean/admin uploads or authorizes their credentials.')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_student_profiles')
    uploaded_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'students'
        ordering = ['roll_number']

    def __str__(self):
        return f'{self.roll_number} - {self.user}'


class DeanProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dean_profile')
    employee_id = models.CharField(max_length=40, unique=True)
    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name='deans')
    designation = models.CharField(max_length=120, default='Dean')
    signature_image = models.FileField(upload_to=secure_signature_path, blank=True, help_text='Digital signature image used on approved OD letters.')
    source_url = models.URLField(blank=True)
    is_official_seed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    transferred_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'deans'
        ordering = ['school__name', 'user__first_name']

    def __str__(self):
        return f'{self.user} - {self.school.code}'


class FacultyProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='faculty_profile')
    employee_id = models.CharField(max_length=40, unique=True)
    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name='faculty')
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='faculty')
    dean = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='faculty_members')
    designation = models.CharField(max_length=120, default='Faculty/Mentor')
    signature_image = models.FileField(upload_to=secure_signature_path, blank=True, help_text='Digital signature image used on approved OD letters.')
    source_url = models.URLField(blank=True)
    is_official_seed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    transferred_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'faculty'
        ordering = ['school__name', 'department__name', 'user__first_name']

    def __str__(self):
        return f'{self.user} - {self.department.code}'

    def transfer_to(self, school, department, dean_user=None):
        self.school = school
        self.department = department
        if dean_user is not None:
            self.dean = dean_user
        self.transferred_at = timezone.now()
        self.save(update_fields=['school', 'department', 'dean', 'transferred_at'])
