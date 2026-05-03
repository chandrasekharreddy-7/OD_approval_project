from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.forms import StaffUserForm, StudentCredentialUploadForm, TransferFacultyForm, TransferStudentForm
from accounts.models import Department, FacultyProfile, StudentProfile, UserRole
from accounts.services import import_student_credentials, preview_student_credentials
from od.forms import ODRuleForm, RemarkForm
from od.models import ODApproval, ODRequest, ODStatus, ODRule
from notifications.utils import notify_user
from security.decorators import dean_required
from security.utils import create_audit_log

User = get_user_model()


def _dean_profile(request):
    return request.user.dean_profile


def _dean_requests(request):
    profile = _dean_profile(request)
    return ODRequest.objects.filter(student__school=profile.school).select_related('student__user', 'student__department', 'faculty_approved_by')


@dean_required
def dashboard(request):
    qs = _dean_requests(request)
    stats = {
        'awaiting': qs.filter(status=ODStatus.FORWARDED_TO_DEAN).count(),
        'approved': qs.filter(status=ODStatus.DEAN_APPROVED).count(),
        'rejected': qs.filter(status=ODStatus.DEAN_REJECTED).count(),
        'total': qs.count(),
    }
    delay_qs = qs.filter(faculty_approved_at__isnull=False, dean_approved_at__isnull=False).annotate(delay=ExpressionWrapper(F('dean_approved_at') - F('faculty_approved_at'), output_field=DurationField()))
    avg_delay = delay_qs.aggregate(avg=Avg('delay'))['avg']
    return render(request, 'dean/dashboard.html', {'stats': stats, 'recent_requests': qs[:8], 'avg_delay': avg_delay})


@dean_required
def approval_requests(request):
    qs = _dean_requests(request)
    status = request.GET.get('status')
    department = request.GET.get('department')
    if status:
        qs = qs.filter(status=status)
    if department:
        qs = qs.filter(student__department_id=department)
    departments = _dean_profile(request).school.departments.filter(is_active=True)
    return render(request, 'dean/approval_requests.html', {'requests': qs, 'statuses': ODStatus.choices, 'departments': departments})


@dean_required
def request_detail(request, pk):
    od_request = get_object_or_404(_dean_requests(request), pk=pk)
    return render(request, 'dean/request_detail.html', {'od_request': od_request, 'form': RemarkForm()})


@dean_required
def approve_request(request, pk):
    od_request = get_object_or_404(_dean_requests(request), pk=pk, status=ODStatus.FORWARDED_TO_DEAN)
    form = RemarkForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        od_request.status = ODStatus.DEAN_APPROVED
        od_request.dean_approved_by = request.user
        od_request.dean_approved_at = timezone.now()
        od_request.save(update_fields=['status', 'dean_approved_by', 'dean_approved_at', 'updated_at'])
        ODApproval.objects.create(od_request=od_request, action_by=request.user, role='Dean', status=ODStatus.DEAN_APPROVED, remarks=form.cleaned_data['remarks'])
        notify_user(od_request.student.user, 'OD approved by Dean', 'Your approved OD letter is ready to download.', reverse('students:request_detail', args=[od_request.pk]))
        create_audit_log(request, 'DEAN_APPROVED_OD', 'ODRequest', od_request.pk, form.cleaned_data['remarks'])
        messages.success(request, 'OD request approved successfully.')
        return redirect('dean:approval_requests')
    return render(request, 'dean/action_form.html', {'form': form, 'od_request': od_request, 'action_label': 'Final Approve'})


@dean_required
def reject_request(request, pk):
    od_request = get_object_or_404(_dean_requests(request), pk=pk, status=ODStatus.FORWARDED_TO_DEAN)
    form = RemarkForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        od_request.status = ODStatus.DEAN_REJECTED
        od_request.save(update_fields=['status', 'updated_at'])
        ODApproval.objects.create(od_request=od_request, action_by=request.user, role='Dean', status=ODStatus.DEAN_REJECTED, remarks=form.cleaned_data['remarks'])
        notify_user(od_request.student.user, 'OD rejected by Dean', form.cleaned_data['remarks'], reverse('students:request_detail', args=[od_request.pk]))
        create_audit_log(request, 'DEAN_REJECTED_OD', 'ODRequest', od_request.pk, form.cleaned_data['remarks'])
        messages.success(request, 'OD request rejected.')
        return redirect('dean:approval_requests')
    return render(request, 'dean/action_form.html', {'form': form, 'od_request': od_request, 'action_label': 'Reject'})


@dean_required
def rules(request):
    profile = _dean_profile(request)
    instance = ODRule.objects.filter(school=profile.school, department__isnull=True).first()
    form = ODRuleForm(request.POST or None, instance=instance)
    form.fields['school'].queryset = type(profile.school).objects.filter(pk=profile.school.pk)
    form.fields['department'].queryset = Department.objects.filter(school=profile.school, is_active=True)
    if request.method == 'POST' and form.is_valid():
        rule = form.save()
        create_audit_log(request, 'OD_RULE_UPDATED', 'ODRule', rule.pk, 'Dean updated OD rules')
        messages.success(request, 'OD rules updated.')
        return redirect('dean:rules')
    rules_qs = ODRule.objects.filter(school=profile.school)
    return render(request, 'dean/rules.html', {'form': form, 'rules': rules_qs})


@dean_required
def manage_faculty(request):
    profile = _dean_profile(request)
    faculty = FacultyProfile.objects.filter(school=profile.school).select_related('user', 'department')
    return render(request, 'dean/manage_faculty.html', {'faculty': faculty})


@dean_required
def add_faculty(request):
    profile = _dean_profile(request)
    form = StaffUserForm(request.POST or None, allowed_role=UserRole.FACULTY, school_scope=profile.school)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        user.faculty_profile.dean = request.user
        user.faculty_profile.save(update_fields=['dean'])
        create_audit_log(request, 'FACULTY_CREATED_BY_DEAN', 'User', user.pk, 'Dean added faculty')
        messages.success(request, 'Faculty added successfully.')
        return redirect('dean:manage_faculty')
    return render(request, 'dean/add_faculty.html', {'form': form})


@dean_required
def transfer_faculty(request, user_id):
    profile = _dean_profile(request)
    faculty = get_object_or_404(FacultyProfile, user_id=user_id, school=profile.school)
    form = TransferFacultyForm(
        request.POST or None,
        school_scope=profile.school,
        initial={
            'school': faculty.school,
            'department': faculty.department,
            'dean': faculty.dean or request.user,
        },
    )
    if request.method == 'POST' and form.is_valid():
        faculty.transfer_to(form.cleaned_data['school'], form.cleaned_data['department'], form.cleaned_data.get('dean') or request.user)
        create_audit_log(request, 'FACULTY_TRANSFERRED_BY_DEAN', 'User', user_id, 'Dean transferred faculty')
        messages.success(request, 'Faculty transferred successfully.')
        return redirect('dean:manage_faculty')
    return render(request, 'dean/transfer_faculty.html', {'form': form, 'faculty': faculty})


@dean_required
def delete_faculty(request, user_id):
    profile = _dean_profile(request)
    faculty = get_object_or_404(FacultyProfile, user_id=user_id, school=profile.school)
    if request.method == 'POST':
        faculty.is_active = False
        faculty.user.is_active = False
        faculty.save(update_fields=['is_active'])
        faculty.user.save(update_fields=['is_active'])
        create_audit_log(request, 'FACULTY_DEACTIVATED_BY_DEAN', 'User', user_id, 'Dean deactivated faculty')
        messages.success(request, 'Faculty deactivated.')
        return redirect('dean:manage_faculty')
    return render(request, 'dean/confirm_delete.html', {'object': faculty.user, 'title': 'Deactivate Faculty'})


@dean_required
def manage_students(request):
    profile = _dean_profile(request)
    students = StudentProfile.objects.filter(school=profile.school).select_related('user', 'department', 'mentor')
    q = request.GET.get('q')
    if q:
        students = students.filter(roll_number__icontains=q) | students.filter(user__email__icontains=q) | students.filter(user__first_name__icontains=q)
    return render(request, 'dean/manage_students.html', {'students': students})


@dean_required
def transfer_student(request, student_id):
    profile = _dean_profile(request)
    student = get_object_or_404(StudentProfile, pk=student_id, school=profile.school)
    form = TransferStudentForm(request.POST or None, school_scope=profile.school, initial={'school': student.school, 'department': student.department, 'mentor': student.mentor, 'year': student.year, 'section': student.section, 'semester': student.semester})
    if request.method == 'POST' and form.is_valid():
        student.department = form.cleaned_data['department']
        student.mentor = form.cleaned_data.get('mentor')
        student.year = form.cleaned_data['year']
        student.section = form.cleaned_data['section']
        student.semester = form.cleaned_data['semester']
        student.save(update_fields=['department', 'mentor', 'year', 'section', 'semester'])
        create_audit_log(request, 'STUDENT_TRANSFERRED_BY_DEAN', 'StudentProfile', student.pk, 'Dean transferred student/mentor mapping')
        messages.success(request, 'Student transferred successfully.')
        return redirect('dean:manage_students')
    return render(request, 'dean/transfer_student.html', {'form': form, 'student': student})


@dean_required
def upload_students(request):
    form = StudentCredentialUploadForm(request.POST or None, request.FILES or None)
    preview_rows = None
    if request.method == 'POST' and form.is_valid():
        if 'preview' in request.POST:
            preview_rows = preview_student_credentials(form.cleaned_data['file'], request.user, scope='dean')
            return render(request, 'dean/upload_students.html', {'form': form, 'preview_rows': preview_rows})
        result = import_student_credentials(form.cleaned_data['file'], request.user, scope='dean')
        create_audit_log(request, 'DEAN_UPLOADED_STUDENTS', 'StudentProfile', '', f'Created={result.created}, updated={result.updated}, skipped={result.skipped}')
        if result.total_success:
            messages.success(request, f'Student credentials uploaded. Created: {result.created}, Updated: {result.updated}.')
        if result.errors:
            messages.warning(request, 'Some rows were skipped: ' + ' | '.join(result.errors[:10]))
        return redirect('dean:upload_students')
    return render(request, 'dean/upload_students.html', {'form': form, 'preview_rows': preview_rows})
