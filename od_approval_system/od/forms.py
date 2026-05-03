from datetime import timedelta
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils import timezone
from .models import ODApproval, ODCategory, ODRequest, ODStatus, ODType, ODRule, UploadedDocument, validate_upload_size


class ODRequestForm(forms.ModelForm):
    proof_document = forms.FileField(
        validators=UploadedDocument._meta.get_field('file').validators,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
    )

    class Meta:
        model = ODRequest
        fields = ['od_type', 'event_title', 'reason', 'from_date', 'to_date', 'place', 'organizer_details']
        widgets = {
            'od_type': forms.Select(attrs={'class': 'form-select'}),
            'event_title': forms.TextInput(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'from_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'to_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'place': forms.TextInput(attrs={'class': 'form-control'}),
            'organizer_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        # ModelForm calls model.full_clean() during form.is_valid(). Attach the
        # current student before validation so ODRequest.clean() can safely apply
        # school/department OD rules and duplicate-date checks.
        if self.student is not None:
            self.instance.student = self.student
        self.fields['od_type'].choices = ODType.choices

    def clean(self):
        cleaned = super().clean()
        from_date = cleaned.get('from_date')
        to_date = cleaned.get('to_date')
        if not self.student or not from_date or not to_date:
            return cleaned
        if from_date > to_date:
            raise ValidationError('From date cannot be after To date.')
        rule = ODRule.objects.filter(school=self.student.school, department=self.student.department, is_active=True).first()
        if not rule:
            rule = ODRule.objects.filter(school=self.student.school, department__isnull=True, is_active=True).first()
        allow_past = rule.allow_past_dates if rule else False
        if not allow_past and from_date < timezone.localdate():
            raise ValidationError('Past dates are not allowed for OD application.')
        blocked_statuses = [ODStatus.FACULTY_REJECTED, ODStatus.DEAN_REJECTED, ODStatus.CANCELLED]
        overlapping = ODRequest.objects.filter(student=self.student, from_date__lte=to_date, to_date__gte=from_date).exclude(status__in=blocked_statuses)
        if overlapping.exists():
            raise ValidationError('You already have an active OD request for these dates.')
        total_days = (to_date - from_date).days + 1
        if rule:
            if total_days > rule.max_days_per_month:
                raise ValidationError(f'This request exceeds the max {rule.max_days_per_month} OD days per request/month rule.')
            active_statuses = [ODStatus.PENDING_FACULTY_REVIEW, ODStatus.FORWARDED_TO_DEAN, ODStatus.DEAN_APPROVED]
            month_start = from_date.replace(day=1)
            existing_month_days = 0
            for req in ODRequest.objects.filter(student=self.student, status__in=active_statuses, from_date__gte=month_start, from_date__month=from_date.month, from_date__year=from_date.year):
                existing_month_days += req.total_days
            if existing_month_days + total_days > rule.max_days_per_month:
                raise ValidationError(f'Monthly OD limit exceeded. Used {existing_month_days}, requested {total_days}, allowed {rule.max_days_per_month}.')
            semester_start = timezone.localdate() - timedelta(days=180)
            existing_semester_days = 0
            for req in ODRequest.objects.filter(student=self.student, status__in=active_statuses, from_date__gte=semester_start):
                existing_semester_days += req.total_days
            if existing_semester_days + total_days > rule.max_days_per_semester:
                raise ValidationError(f'Semester OD limit exceeded. Used {existing_semester_days}, requested {total_days}, allowed {rule.max_days_per_semester}.')
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.student = self.student
        if commit:
            obj.full_clean()
            obj.save()
            upload = self.cleaned_data['proof_document']
            UploadedDocument.objects.create(
                od_request=obj,
                uploaded_by=self.student.user,
                file=upload,
                original_filename=upload.name,
                content_type=getattr(upload, 'content_type', ''),
                size_bytes=upload.size,
            )
        return obj


class RemarkForm(forms.Form):
    remarks = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter action remarks'}), max_length=1000)


class ODRuleForm(forms.ModelForm):
    class Meta:
        model = ODRule
        fields = ['school', 'department', 'max_days_per_month', 'max_days_per_semester', 'allow_past_dates', 'is_active']
        widgets = {
            'school': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'max_days_per_month': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_days_per_semester': forms.NumberInput(attrs={'class': 'form-control'}),
            'allow_past_dates': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ODCategoryForm(forms.ModelForm):
    class Meta:
        model = ODCategory
        fields = ['name', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
