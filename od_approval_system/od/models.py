import os
import uuid
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from accounts.models import Department, School, StudentProfile


class ODStatus(models.TextChoices):
    PENDING_FACULTY_REVIEW = 'PENDING_FACULTY_REVIEW', 'Pending Faculty Review'
    FACULTY_APPROVED = 'FACULTY_APPROVED', 'Faculty Approved'
    FORWARDED_TO_DEAN = 'FORWARDED_TO_DEAN', 'Forwarded to Dean'
    DEAN_APPROVED = 'DEAN_APPROVED', 'Dean Approved'
    DEAN_REJECTED = 'DEAN_REJECTED', 'Dean Rejected'
    FACULTY_REJECTED = 'FACULTY_REJECTED', 'Faculty Rejected'
    CANCELLED = 'CANCELLED', 'Cancelled'


class ODType(models.TextChoices):
    SPORTS = 'sports', 'Sports'
    WORKSHOP = 'workshop', 'Workshop'
    SEMINAR = 'seminar', 'Seminar'
    INTERNSHIP = 'internship', 'Internship'
    PLACEMENT = 'placement', 'Placement'
    CULTURAL = 'cultural event', 'Cultural Event'
    TECHNICAL = 'technical event', 'Technical Event'
    NSS_NCC = 'NSS/NCC', 'NSS/NCC'
    OTHER = 'other', 'Other'


class ODCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'od_categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class ODRule(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='od_rules')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True, related_name='od_rules')
    max_days_per_month = models.PositiveIntegerField(default=5)
    max_days_per_semester = models.PositiveIntegerField(default=20)
    allow_past_dates = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'od_rules'
        unique_together = ('school', 'department')
        ordering = ['school__name', 'department__name']

    def __str__(self):
        scope = self.department.name if self.department else self.school.name
        return f'OD Rule - {scope}'


def validate_upload_size(uploaded_file):
    max_mb = getattr(settings, 'MAX_UPLOAD_SIZE_MB', 5)
    if uploaded_file.size > max_mb * 1024 * 1024:
        raise ValidationError(f'File size must be under {max_mb} MB.')


def secure_document_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'od_documents/{timezone.now().strftime("%Y/%m")}/{uuid.uuid4().hex}{ext}'


class ODRequest(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='od_requests')
    od_type = models.CharField(max_length=30, choices=ODType.choices)
    event_title = models.CharField(max_length=180)
    reason = models.TextField()
    from_date = models.DateField()
    to_date = models.DateField()
    place = models.CharField(max_length=180)
    organizer_details = models.TextField()
    status = models.CharField(max_length=40, choices=ODStatus.choices, default=ODStatus.PENDING_FACULTY_REVIEW)
    faculty_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='faculty_approved_ods')
    dean_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='dean_approved_ods')
    faculty_approved_at = models.DateTimeField(null=True, blank=True)
    dean_approved_at = models.DateTimeField(null=True, blank=True)
    verification_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'od_requests'
        ordering = ['-created_at']

    def __str__(self):
        roll_number = getattr(getattr(self, 'student', None), 'roll_number', 'Unassigned')
        return f'{roll_number} - {self.event_title}'

    @property
    def total_days(self):
        return (self.to_date - self.from_date).days + 1

    @property
    def is_pending(self):
        return self.status == ODStatus.PENDING_FACULTY_REVIEW

    @property
    def status_label(self):
        return self.get_status_display()

    def clean(self):
        if self.from_date and self.to_date and self.from_date > self.to_date:
            raise ValidationError('From date cannot be after To date.')

        # During ModelForm validation, a new ODRequest may not yet have a student
        # unless the view/form attaches it first. Skip student-scoped rule checks
        # until student is available; ODRequestForm attaches it before validation.
        if not getattr(self, 'student_id', None):
            return

        if self.from_date and not getattr(settings, 'ALLOW_PAST_OD_DATES', False):
            rule = ODRule.objects.filter(school=self.student.school, department=self.student.department, is_active=True).first()
            if not rule:
                rule = ODRule.objects.filter(school=self.student.school, department__isnull=True, is_active=True).first()
            allow_past = rule.allow_past_dates if rule else False
            if not allow_past and self.from_date < timezone.localdate():
                raise ValidationError('Past OD dates are not allowed.')

    def overlaps_existing(self):
        if not getattr(self, 'student_id', None) or not self.from_date or not self.to_date:
            return False
        blocked_statuses = [ODStatus.FACULTY_REJECTED, ODStatus.DEAN_REJECTED, ODStatus.CANCELLED]
        return ODRequest.objects.filter(
            student=self.student,
            from_date__lte=self.to_date,
            to_date__gte=self.from_date,
        ).exclude(status__in=blocked_statuses).exclude(pk=self.pk).exists()

    def semester_start(self):
        return timezone.localdate() - timedelta(days=180)


class ODApproval(models.Model):
    od_request = models.ForeignKey(ODRequest, on_delete=models.CASCADE, related_name='approvals')
    action_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    role = models.CharField(max_length=20)
    status = models.CharField(max_length=40, choices=ODStatus.choices)
    remarks = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'od_approvals'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.od_request_id} - {self.status} by {self.role}'


class UploadedDocument(models.Model):
    od_request = models.ForeignKey(ODRequest, on_delete=models.CASCADE, related_name='uploaded_documents')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    file = models.FileField(
        upload_to=secure_document_path,
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png']), validate_upload_size],
    )
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'uploaded_documents'
        ordering = ['-created_at']

    def __str__(self):
        return self.original_filename
