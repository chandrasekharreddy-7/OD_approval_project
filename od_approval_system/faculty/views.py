from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.forms import StudentCredentialUploadForm
from accounts.models import StudentProfile
from accounts.services import import_student_credentials, preview_student_credentials
from od.forms import RemarkForm
from od.models import ODApproval, ODRequest, ODStatus
from notifications.utils import notify_user
from security.decorators import faculty_required
from security.utils import create_audit_log


def _faculty_requests(request):
    return ODRequest.objects.filter(student__mentor=request.user).select_related('student__user', 'student__department', 'student__school')


@faculty_required
def dashboard(request):
    qs = _faculty_requests(request)
    stats = {
        'pending': qs.filter(status=ODStatus.PENDING_FACULTY_REVIEW).count(),
        'forwarded': qs.filter(status=ODStatus.FORWARDED_TO_DEAN).count(),
        'approved': qs.filter(status=ODStatus.DEAN_APPROVED).count(),
        'rejected': qs.filter(status__in=[ODStatus.FACULTY_REJECTED, ODStatus.DEAN_REJECTED]).count(),
    }
    return render(request, 'faculty/dashboard.html', {'stats': stats, 'recent_requests': qs[:8]})


@faculty_required
def pending_requests(request):
    qs = _faculty_requests(request)
    status = request.GET.get('status')
    department = request.GET.get('department')
    year = request.GET.get('year')
    section = request.GET.get('section')
    date = request.GET.get('date')
    if status:
        qs = qs.filter(status=status)
    if department:
        qs = qs.filter(student__department_id=department)
    if year:
        qs = qs.filter(student__year=year)
    if section:
        qs = qs.filter(student__section__iexact=section)
    if date:
        qs = qs.filter(from_date__lte=date, to_date__gte=date)
    departments = request.user.faculty_profile.school.departments.filter(is_active=True) if hasattr(request.user, 'faculty_profile') else []
    return render(request, 'faculty/pending_requests.html', {'requests': qs, 'statuses': ODStatus.choices, 'departments': departments})


@faculty_required
def request_detail(request, pk):
    od_request = get_object_or_404(_faculty_requests(request), pk=pk)
    return render(request, 'faculty/request_detail.html', {'od_request': od_request, 'form': RemarkForm()})


@faculty_required
def approve_request(request, pk):
    od_request = get_object_or_404(_faculty_requests(request), pk=pk, status=ODStatus.PENDING_FACULTY_REVIEW)
    form = RemarkForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        od_request.status = ODStatus.FORWARDED_TO_DEAN
        od_request.faculty_approved_by = request.user
        od_request.faculty_approved_at = timezone.now()
        od_request.save(update_fields=['status', 'faculty_approved_by', 'faculty_approved_at', 'updated_at'])
        ODApproval.objects.create(od_request=od_request, action_by=request.user, role='Faculty', status=ODStatus.FACULTY_APPROVED, remarks=form.cleaned_data['remarks'])
        notify_user(od_request.student.user, 'OD forwarded to Dean', f'Your OD request "{od_request.event_title}" was approved by faculty.', reverse('students:request_detail', args=[od_request.pk]))
        dean_user = getattr(getattr(request.user, 'faculty_profile', None), 'dean', None)
        if dean_user:
            notify_user(dean_user, 'OD awaiting Dean approval', f'Faculty forwarded {od_request.student.roll_number} OD request.', reverse('dean:request_detail', args=[od_request.pk]))
        create_audit_log(request, 'FACULTY_APPROVED_OD', 'ODRequest', od_request.pk, form.cleaned_data['remarks'])
        messages.success(request, 'Request approved and forwarded to Dean.')
        return redirect('faculty:pending_requests')
    return render(request, 'faculty/action_form.html', {'form': form, 'od_request': od_request, 'action_label': 'Approve and Forward'})


@faculty_required
def reject_request(request, pk):
    od_request = get_object_or_404(_faculty_requests(request), pk=pk, status=ODStatus.PENDING_FACULTY_REVIEW)
    form = RemarkForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        od_request.status = ODStatus.FACULTY_REJECTED
        od_request.save(update_fields=['status', 'updated_at'])
        ODApproval.objects.create(od_request=od_request, action_by=request.user, role='Faculty', status=ODStatus.FACULTY_REJECTED, remarks=form.cleaned_data['remarks'])
        notify_user(od_request.student.user, 'OD rejected by Faculty', form.cleaned_data['remarks'], reverse('students:request_detail', args=[od_request.pk]))
        create_audit_log(request, 'FACULTY_REJECTED_OD', 'ODRequest', od_request.pk, form.cleaned_data['remarks'])
        messages.success(request, 'Request rejected.')
        return redirect('faculty:pending_requests')
    return render(request, 'faculty/action_form.html', {'form': form, 'od_request': od_request, 'action_label': 'Reject'})


@faculty_required
def student_history(request, student_id):
    student = get_object_or_404(StudentProfile, pk=student_id, mentor=request.user)
    return render(request, 'faculty/student_history.html', {'student': student, 'requests': student.od_requests.all()})


@faculty_required
def upload_students(request):
    form = StudentCredentialUploadForm(request.POST or None, request.FILES or None)
    preview_rows = None
    if request.method == 'POST' and form.is_valid():
        if 'preview' in request.POST:
            preview_rows = preview_student_credentials(form.cleaned_data['file'], request.user, scope='faculty')
            return render(request, 'faculty/upload_students.html', {'form': form, 'preview_rows': preview_rows})
        result = import_student_credentials(form.cleaned_data['file'], request.user, scope='faculty')
        create_audit_log(request, 'FACULTY_UPLOADED_STUDENTS', 'StudentProfile', '', f'Created={result.created}, updated={result.updated}, skipped={result.skipped}')
        if result.total_success:
            messages.success(request, f'Student credentials uploaded. Created: {result.created}, Updated: {result.updated}.')
        if result.errors:
            messages.warning(request, 'Some rows were skipped: ' + ' | '.join(result.errors[:10]))
        return redirect('faculty:upload_students')
    return render(request, 'faculty/upload_students.html', {'form': form, 'preview_rows': preview_rows})
