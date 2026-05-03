from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from od.forms import ODRequestForm
from od.models import ODApproval, ODRequest, ODStatus
from od.pdf import build_od_letter_response
from notifications.utils import notify_user
from security.decorators import student_required
from security.utils import create_audit_log


def _student_profile(request):
    return request.user.student_profile


@student_required
def dashboard(request):
    student = _student_profile(request)
    qs = student.od_requests.all()
    stats = {
        'total': qs.count(),
        'pending': qs.filter(status=ODStatus.PENDING_FACULTY_REVIEW).count(),
        'approved': qs.filter(status=ODStatus.DEAN_APPROVED).count(),
        'rejected': qs.filter(status__in=[ODStatus.FACULTY_REJECTED, ODStatus.DEAN_REJECTED]).count(),
    }
    return render(request, 'students/dashboard.html', {'stats': stats, 'recent_requests': qs[:5]})


@student_required
def apply_od(request):
    student = _student_profile(request)
    form = ODRequestForm(request.POST or None, request.FILES or None, student=student)
    if request.method == 'POST' and form.is_valid():
        od_request = form.save()
        ODApproval.objects.create(od_request=od_request, action_by=request.user, role='Student', status=ODStatus.PENDING_FACULTY_REVIEW, remarks='Submitted by student')
        if student.mentor:
            notify_user(student.mentor, 'New OD request', f'{student.roll_number} submitted an OD request.', reverse('faculty:request_detail', args=[od_request.pk]))
        create_audit_log(request, 'OD_CREATED', 'ODRequest', od_request.pk, f'Created OD request: {od_request.event_title}')
        messages.success(request, 'OD request submitted successfully.')
        return redirect('students:my_requests')
    return render(request, 'students/apply_od.html', {'form': form})


@student_required
def my_requests(request):
    student = _student_profile(request)
    requests = student.od_requests.all()
    status = request.GET.get('status')
    q = request.GET.get('q')
    if status:
        requests = requests.filter(status=status)
    if q:
        requests = requests.filter(event_title__icontains=q)
    return render(request, 'students/my_requests.html', {'requests': requests, 'statuses': ODStatus.choices})


@student_required
def request_detail(request, pk):
    od_request = get_object_or_404(ODRequest, pk=pk, student=_student_profile(request))
    return render(request, 'students/request_detail.html', {'od_request': od_request})


@student_required
def cancel_request(request, pk):
    od_request = get_object_or_404(ODRequest, pk=pk, student=_student_profile(request), status=ODStatus.PENDING_FACULTY_REVIEW)
    if request.method == 'POST':
        od_request.status = ODStatus.CANCELLED
        od_request.save(update_fields=['status', 'updated_at'])
        ODApproval.objects.create(od_request=od_request, action_by=request.user, role='Student', status=ODStatus.CANCELLED, remarks='Cancelled by student')
        create_audit_log(request, 'OD_CANCELLED', 'ODRequest', od_request.pk, 'Student cancelled pending request')
        messages.success(request, 'OD request cancelled.')
        return redirect('students:my_requests')
    return render(request, 'students/confirm_action.html', {'title': 'Cancel OD Request', 'object': od_request, 'action_label': 'Cancel Request'})


@student_required
def download_od_pdf(request, pk):
    od_request = get_object_or_404(ODRequest, pk=pk, student=_student_profile(request), status=ODStatus.DEAN_APPROVED)
    create_audit_log(request, 'OD_PDF_DOWNLOADED', 'ODRequest', od_request.pk, 'Student downloaded approved OD letter')
    return build_od_letter_response(request, od_request)
