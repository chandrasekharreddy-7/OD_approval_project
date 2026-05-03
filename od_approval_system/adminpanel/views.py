import csv
import secrets
import string
from io import TextIOWrapper
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.forms import DepartmentForm, SchoolForm, StaffUserForm, StudentCredentialUploadForm, TransferDeanForm, TransferFacultyForm, TransferStudentForm
from accounts.models import DeanProfile, Department, FacultyProfile, School, StudentProfile, UserRole
from accounts.services import import_student_credentials, preview_student_credentials
from od.forms import ODCategoryForm, ODRuleForm
from od.models import ODCategory, ODRequest, ODStatus, ODRule
from security.decorators import admin_required
from security.models import AuditLog
from security.utils import create_audit_log

User = get_user_model()


def _random_password(length=12):
    alphabet = string.ascii_letters + string.digits + '!@#$%'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@admin_required
def dashboard(request):
    stats = {
        'students': StudentProfile.objects.count(),
        'faculty': FacultyProfile.objects.count(),
        'deans': DeanProfile.objects.count(),
        'requests': ODRequest.objects.count(),
        'pending': ODRequest.objects.filter(status__in=[ODStatus.PENDING_FACULTY_REVIEW, ODStatus.FORWARDED_TO_DEAN]).count(),
        'approved': ODRequest.objects.filter(status=ODStatus.DEAN_APPROVED).count(),
    }
    recent_requests = ODRequest.objects.select_related('student__user', 'student__department').all()[:8]
    return render(request, 'adminpanel/dashboard.html', {'stats': stats, 'recent_requests': recent_requests})


@admin_required
def manage_students(request):
    students = StudentProfile.objects.select_related('user', 'school', 'department', 'mentor').all()
    q = request.GET.get('q')
    if q:
        students = students.filter(roll_number__icontains=q) | students.filter(user__email__icontains=q) | students.filter(user__first_name__icontains=q)
    return render(request, 'adminpanel/manage_students.html', {'students': students})


@admin_required
def transfer_student(request, student_id):
    student = get_object_or_404(StudentProfile, pk=student_id)
    form = TransferStudentForm(request.POST or None, initial={'school': student.school, 'department': student.department, 'mentor': student.mentor, 'year': student.year, 'section': student.section, 'semester': student.semester})
    if request.method == 'POST' and form.is_valid():
        student.school = form.cleaned_data['school']
        student.department = form.cleaned_data['department']
        student.mentor = form.cleaned_data.get('mentor')
        student.year = form.cleaned_data['year']
        student.section = form.cleaned_data['section']
        student.semester = form.cleaned_data['semester']
        student.save(update_fields=['school', 'department', 'mentor', 'year', 'section', 'semester'])
        create_audit_log(request, 'STUDENT_TRANSFERRED_BY_ADMIN', 'StudentProfile', student.pk, 'Admin transferred student/mentor mapping')
        messages.success(request, 'Student transferred successfully.')
        return redirect('adminpanel:manage_students')
    return render(request, 'adminpanel/transfer_student.html', {'form': form, 'student': student})


@admin_required
def manage_users(request):
    users = User.objects.all().order_by('role', 'first_name')
    role = request.GET.get('role')
    q = request.GET.get('q')
    if role:
        users = users.filter(role=role)
    if q:
        users = users.filter(email__icontains=q) | users.filter(first_name__icontains=q) | users.filter(last_name__icontains=q)
    return render(request, 'adminpanel/manage_users.html', {'users': users, 'roles': UserRole.choices})


@admin_required
def add_user(request):
    form = StaffUserForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        create_audit_log(request, 'USER_CREATED', 'User', user.pk, f'Admin created user {user.email}')
        messages.success(request, 'User created successfully.')
        return redirect('adminpanel:manage_users')
    return render(request, 'adminpanel/add_user.html', {'form': form})


@admin_required
def deactivate_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        create_audit_log(request, 'USER_STATUS_TOGGLED', 'User', user.pk, f'User active={user.is_active}')
        messages.success(request, 'User status updated.')
        return redirect('adminpanel:manage_users')
    return render(request, 'adminpanel/confirm_action.html', {'title': 'Toggle User Status', 'object': user, 'action_label': 'Confirm'})


@admin_required
def reset_password(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        password = _random_password()
        user.set_password(password)
        user.must_change_password = True
        user.save(update_fields=['password', 'must_change_password'])
        create_audit_log(request, 'PASSWORD_RESET', 'User', user.pk, 'Admin reset password')
        messages.success(request, f'New temporary password for {user.email}: {password}')
        return redirect('adminpanel:manage_users')
    return render(request, 'adminpanel/confirm_action.html', {'title': 'Reset Password', 'object': user, 'action_label': 'Reset Password'})


@admin_required
def manage_deans(request):
    deans = DeanProfile.objects.select_related('user', 'school').all()
    return render(request, 'adminpanel/manage_deans.html', {'deans': deans})


@admin_required
def add_dean(request):
    form = StaffUserForm(request.POST or None, allowed_role=UserRole.DEAN)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        create_audit_log(request, 'DEAN_CREATED', 'User', user.pk, 'Admin added dean')
        messages.success(request, 'Dean added successfully.')
        return redirect('adminpanel:manage_deans')
    return render(request, 'adminpanel/add_dean.html', {'form': form})


@admin_required
def transfer_dean(request, user_id):
    dean = get_object_or_404(DeanProfile, user_id=user_id)
    form = TransferDeanForm(request.POST or None, initial={'school': dean.school})
    if request.method == 'POST' and form.is_valid():
        dean.school = form.cleaned_data['school']
        dean.save(update_fields=['school'])
        create_audit_log(request, 'DEAN_TRANSFERRED', 'User', user_id, 'Admin transferred dean to another school')
        messages.success(request, 'Dean transferred successfully.')
        return redirect('adminpanel:manage_deans')
    return render(request, 'adminpanel/transfer_dean.html', {'form': form, 'dean': dean})


@admin_required
def delete_dean(request, user_id):
    dean = get_object_or_404(DeanProfile, user_id=user_id)
    if request.method == 'POST':
        dean.is_active = False
        dean.user.is_active = False
        dean.save(update_fields=['is_active'])
        dean.user.save(update_fields=['is_active'])
        create_audit_log(request, 'DEAN_DEACTIVATED', 'User', user_id, 'Admin deactivated dean')
        messages.success(request, 'Dean deactivated.')
        return redirect('adminpanel:manage_deans')
    return render(request, 'adminpanel/confirm_action.html', {'title': 'Deactivate Dean', 'object': dean.user, 'action_label': 'Deactivate'})


@admin_required
def manage_faculty(request):
    faculty = FacultyProfile.objects.select_related('user', 'school', 'department', 'dean').all()
    return render(request, 'adminpanel/manage_faculty.html', {'faculty': faculty})


@admin_required
def transfer_faculty(request, user_id):
    faculty = get_object_or_404(FacultyProfile, user_id=user_id)
    form = TransferFacultyForm(request.POST or None, initial={'school': faculty.school, 'department': faculty.department, 'dean': faculty.dean})
    if request.method == 'POST' and form.is_valid():
        faculty.transfer_to(form.cleaned_data['school'], form.cleaned_data['department'], form.cleaned_data.get('dean'))
        create_audit_log(request, 'FACULTY_TRANSFERRED_BY_ADMIN', 'User', user_id, 'Admin transferred faculty')
        messages.success(request, 'Faculty transferred successfully.')
        return redirect('adminpanel:manage_faculty')
    return render(request, 'adminpanel/transfer_faculty.html', {'form': form, 'faculty': faculty})


@admin_required
def delete_faculty(request, user_id):
    faculty = get_object_or_404(FacultyProfile, user_id=user_id)
    if request.method == 'POST':
        faculty.is_active = False
        faculty.user.is_active = False
        faculty.save(update_fields=['is_active'])
        faculty.user.save(update_fields=['is_active'])
        create_audit_log(request, 'FACULTY_DEACTIVATED_BY_ADMIN', 'User', user_id, 'Admin deactivated faculty')
        messages.success(request, 'Faculty deactivated.')
        return redirect('adminpanel:manage_faculty')
    return render(request, 'adminpanel/confirm_action.html', {'title': 'Deactivate Faculty', 'object': faculty.user, 'action_label': 'Deactivate'})


@admin_required
def schools_departments(request):
    school_form = SchoolForm(prefix='school')
    department_form = DepartmentForm(prefix='department')
    if request.method == 'POST':
        if 'save_school' in request.POST:
            school_form = SchoolForm(request.POST, prefix='school')
            if school_form.is_valid():
                school = school_form.save()
                create_audit_log(request, 'SCHOOL_SAVED', 'School', school.pk, 'Admin saved school')
                messages.success(request, 'School saved.')
                return redirect('adminpanel:schools_departments')
        if 'save_department' in request.POST:
            department_form = DepartmentForm(request.POST, prefix='department')
            if department_form.is_valid():
                department = department_form.save()
                create_audit_log(request, 'DEPARTMENT_SAVED', 'Department', department.pk, 'Admin saved department')
                messages.success(request, 'Department saved.')
                return redirect('adminpanel:schools_departments')
    return render(request, 'adminpanel/schools_departments.html', {
        'school_form': school_form,
        'department_form': department_form,
        'schools': School.objects.all(),
        'departments': Department.objects.select_related('school').all(),
    })


@admin_required
def od_categories(request):
    form = ODCategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        category = form.save()
        create_audit_log(request, 'OD_CATEGORY_SAVED', 'ODCategory', category.pk, 'Admin saved OD category')
        messages.success(request, 'OD category saved.')
        return redirect('adminpanel:od_categories')
    return render(request, 'adminpanel/od_categories.html', {'form': form, 'categories': ODCategory.objects.all()})


@admin_required
def od_rules(request):
    form = ODRuleForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        rule = form.save()
        create_audit_log(request, 'OD_RULE_SAVED_BY_ADMIN', 'ODRule', rule.pk, 'Admin saved OD rule')
        messages.success(request, 'OD rule saved.')
        return redirect('adminpanel:od_rules')
    return render(request, 'adminpanel/od_rules.html', {'form': form, 'rules': ODRule.objects.select_related('school', 'department')})


@admin_required
def all_od_requests(request):
    qs = ODRequest.objects.select_related('student__user', 'student__department', 'student__school')
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)
    return render(request, 'adminpanel/all_od_requests.html', {'requests': qs, 'statuses': ODStatus.choices})


@admin_required
def audit_logs(request):
    logs = AuditLog.objects.select_related('user').all()[:500]
    return render(request, 'adminpanel/audit_logs.html', {'logs': logs})


@admin_required
def import_students(request):
    form = StudentCredentialUploadForm(request.POST or None, request.FILES or None)
    preview_rows = None
    if request.method == 'POST' and form.is_valid():
        if 'preview' in request.POST:
            preview_rows = preview_student_credentials(form.cleaned_data['file'], request.user, scope='admin')
            return render(request, 'adminpanel/import_students.html', {'form': form, 'preview_rows': preview_rows})
        result = import_student_credentials(form.cleaned_data['file'], request.user, scope='admin')
        create_audit_log(request, 'STUDENTS_IMPORTED', 'StudentProfile', '', f'Created={result.created}, updated={result.updated}, skipped={result.skipped}')
        if result.total_success:
            messages.success(request, f'Student credentials imported. Created: {result.created}, Updated: {result.updated}.')
        if result.errors:
            messages.warning(request, 'Some rows were skipped: ' + ' | '.join(result.errors[:10]))
        return redirect('adminpanel:import_students')
    return render(request, 'adminpanel/import_students.html', {'form': form, 'preview_rows': preview_rows})
