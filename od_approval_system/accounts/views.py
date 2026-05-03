from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from django.contrib.auth.forms import PasswordChangeForm
from .forms import LoginForm, ProfileForm, SignatureUploadForm, StudentRegistrationForm
from .models import UserRole
from security.models import LoginAttempt
from security.utils import create_audit_log, get_client_ip


def home(request):
    return render(request, 'accounts/home.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:redirect')
    form = LoginForm(request.POST or None)
    ip = get_client_ip(request)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'].lower()
        window = timezone.now() - timedelta(minutes=15)
        failed_count = LoginAttempt.objects.filter(email=email, ip_address=ip, successful=False, created_at__gte=window).count()
        if failed_count >= 5:
            messages.error(request, 'Too many failed login attempts. Try again after 15 minutes.')
            return render(request, 'accounts/login.html', {'form': form})
        user = authenticate(request, username=email, password=form.cleaned_data['password'])
        if user is not None and user.is_active:
            if user.role == UserRole.STUDENT:
                profile = getattr(user, 'student_profile', None)
                if not profile or not profile.is_active or not profile.staff_uploaded_login:
                    LoginAttempt.objects.create(email=email, ip_address=ip, successful=False)
                    create_audit_log(request, 'STUDENT_LOGIN_BLOCKED', 'User', user.pk, 'Student login blocked because staff-uploaded credentials/profile are missing or inactive')
                    messages.error(request, 'Student login is allowed only after faculty/dean/admin uploads and authorizes your email, roll number, and password.')
                    return render(request, 'accounts/login.html', {'form': form})
            login(request, user)
            LoginAttempt.objects.create(email=email, ip_address=ip, successful=True)
            create_audit_log(request, 'LOGIN_SUCCESS', 'User', user.pk, 'User logged in')
            return redirect('accounts:redirect')
        LoginAttempt.objects.create(email=email, ip_address=ip, successful=False)
        messages.error(request, 'Invalid email/password or inactive account.')
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        create_audit_log(request, 'LOGOUT', 'User', request.user.pk, 'User logged out')
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('accounts:login')


@login_required
def role_redirect(request):
    user = request.user
    if user.is_superuser or user.role == UserRole.ADMIN:
        return redirect('adminpanel:dashboard')
    if user.role == UserRole.DEAN:
        return redirect('dean:dashboard')
    if user.role == UserRole.FACULTY:
        return redirect('faculty:dashboard')
    return redirect('students:dashboard')


def register_student(request):
    # Student accounts are now controlled by faculty/dean/admin-uploaded credentials.
    # This prevents unauthorized self-registration inside the university OD workflow.
    return render(request, 'accounts/register_student.html', {'registration_locked': True})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    signature_form = SignatureUploadForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if 'save_profile' in request.POST and form.is_valid():
            form.save()
            create_audit_log(request, 'PROFILE_UPDATED', 'User', request.user.pk, 'Profile updated')
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
        if 'save_signature' in request.POST and signature_form.is_valid():
            upload = signature_form.cleaned_data.get('signature_image')
            profile = getattr(request.user, 'faculty_profile', None) or getattr(request.user, 'dean_profile', None)
            if not profile:
                messages.error(request, 'Digital signature upload is available only for faculty and dean users.')
            elif upload:
                profile.signature_image = upload
                profile.save(update_fields=['signature_image'])
                create_audit_log(request, 'SIGNATURE_UPDATED', 'User', request.user.pk, 'Digital signature updated')
                messages.success(request, 'Digital signature updated successfully.')
                return redirect('accounts:profile')
    signature_profile = getattr(request.user, 'faculty_profile', None) or getattr(request.user, 'dean_profile', None)
    return render(request, 'accounts/profile.html', {'form': form, 'signature_form': signature_form, 'signature_profile': signature_profile})


@login_required
def password_change_required(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    for field in form.fields.values():
        field.widget.attrs.update({'class': 'form-control'})
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        user.must_change_password = False
        user.save(update_fields=['must_change_password'])
        update_session_auth_hash(request, user)
        create_audit_log(request, 'PASSWORD_CHANGED', 'User', user.pk, 'User changed temporary password')
        messages.success(request, 'Password changed successfully.')
        return redirect('accounts:redirect')
    return render(request, 'accounts/password_change_required.html', {'form': form})
