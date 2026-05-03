import csv
from io import BytesIO
from django.http import HttpResponse
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from accounts.models import UserRole
from od.models import ODRequest, ODStatus
from security.decorators import role_required
from security.utils import create_audit_log


def _visible_requests(request):
    qs = ODRequest.objects.select_related('student__user', 'student__department', 'student__school', 'faculty_approved_by', 'dean_approved_by')
    if request.user.role == UserRole.STUDENT:
        return qs.filter(student=request.user.student_profile)
    if request.user.role == UserRole.FACULTY:
        return qs.filter(student__mentor=request.user)
    if request.user.role == UserRole.DEAN:
        return qs.filter(student__school=request.user.dean_profile.school)
    return qs


def _filtered_requests(request):
    qs = _visible_requests(request)
    report_type = request.GET.get('type')
    status = request.GET.get('status')
    department = request.GET.get('department')
    school = request.GET.get('school')
    month = request.GET.get('month')
    if status:
        qs = qs.filter(status=status)
    if department:
        qs = qs.filter(student__department_id=department)
    if school and request.user.role == UserRole.ADMIN:
        qs = qs.filter(student__school_id=school)
    if month:
        year, m = month.split('-')
        qs = qs.filter(from_date__year=int(year), from_date__month=int(m))
    if report_type == 'pending':
        qs = qs.filter(status__in=[ODStatus.PENDING_FACULTY_REVIEW, ODStatus.FORWARDED_TO_DEAN])
    elif report_type == 'rejected':
        qs = qs.filter(status__in=[ODStatus.FACULTY_REJECTED, ODStatus.DEAN_REJECTED])
    elif report_type == 'approved':
        qs = qs.filter(status=ODStatus.DEAN_APPROVED)
    return qs


@role_required(UserRole.ADMIN, UserRole.DEAN)
def index(request):
    qs = _filtered_requests(request)
    return render(request, 'reports/index.html', {'requests': qs[:200], 'statuses': ODStatus.choices})


@role_required(UserRole.ADMIN, UserRole.DEAN)
def export_excel(request):
    qs = _filtered_requests(request)
    wb = Workbook()
    ws = wb.active
    ws.title = 'OD Reports'
    headers = ['ID', 'Student', 'Roll Number', 'School', 'Department', 'OD Type', 'Event', 'From', 'To', 'Status', 'Faculty', 'Dean']
    ws.append(headers)
    for obj in qs:
        ws.append([
            obj.pk,
            obj.student.user.get_full_name(),
            obj.student.roll_number,
            obj.student.school.name,
            obj.student.department.name,
            obj.get_od_type_display(),
            obj.event_title,
            obj.from_date.isoformat(),
            obj.to_date.isoformat(),
            obj.get_status_display(),
            obj.faculty_approved_by.get_full_name() if obj.faculty_approved_by else '',
            obj.dean_approved_by.get_full_name() if obj.dean_approved_by else '',
        ])
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    create_audit_log(request, 'REPORT_EXCEL_EXPORTED', 'ODRequest', '', 'Exported OD Excel report')
    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="od_report.xlsx"'
    return response


@role_required(UserRole.ADMIN, UserRole.DEAN)
def export_csv(request):
    qs = _filtered_requests(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="od_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Student', 'Roll Number', 'School', 'Department', 'OD Type', 'Event', 'From', 'To', 'Status'])
    for obj in qs:
        writer.writerow([obj.pk, obj.student.user.get_full_name(), obj.student.roll_number, obj.student.school.name, obj.student.department.name, obj.get_od_type_display(), obj.event_title, obj.from_date, obj.to_date, obj.get_status_display()])
    create_audit_log(request, 'REPORT_CSV_EXPORTED', 'ODRequest', '', 'Exported OD CSV report')
    return response


@role_required(UserRole.ADMIN, UserRole.DEAN)
def export_pdf(request):
    qs = list(_filtered_requests(request)[:80])
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40
    pdf.setFont('Helvetica-Bold', 16)
    pdf.drawString(40, y, 'SAI UNIVERSITY - OD REPORT')
    y -= 30
    pdf.setFont('Helvetica', 8)
    for obj in qs:
        line = f'{obj.pk} | {obj.student.roll_number} | {obj.student.user.get_full_name()} | {obj.student.department.code} | {obj.from_date} to {obj.to_date} | {obj.get_status_display()}'
        pdf.drawString(40, y, line[:130])
        y -= 14
        if y < 50:
            pdf.showPage()
            y = height - 40
            pdf.setFont('Helvetica', 8)
    pdf.save()
    buffer.seek(0)
    create_audit_log(request, 'REPORT_PDF_EXPORTED', 'ODRequest', '', 'Exported OD PDF report')
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="od_report.pdf"'
    return response


@role_required(UserRole.ADMIN, UserRole.DEAN, UserRole.FACULTY, UserRole.STUDENT)
def calendar_view(request):
    today = timezone.localdate()
    year = int(request.GET.get('year') or today.year)
    month = int(request.GET.get('month') or today.month)
    qs = _visible_requests(request).filter(from_date__year=year, from_date__month=month)
    events_by_day = {}
    for obj in qs:
        day = obj.from_date.day
        events_by_day.setdefault(day, []).append(obj)
    # Simple month grid without external JS dependency.
    import calendar as pycalendar
    cal = pycalendar.Calendar(firstweekday=0)
    weeks = []
    for week in cal.monthdayscalendar(year, month):
        weeks.append([{'day': day, 'events': events_by_day.get(day, [])} for day in week])
    months = [(i, pycalendar.month_name[i]) for i in range(1, 13)]
    return render(request, 'reports/calendar.html', {
        'weeks': weeks,
        'month': month,
        'year': year,
        'months': months,
        'month_name': pycalendar.month_name[month],
    })


@role_required(UserRole.ADMIN, UserRole.DEAN)
def analytics(request):
    qs = _visible_requests(request)
    total = qs.count() or 1
    status_counts = qs.values('status').annotate(total=Count('id')).order_by('status')
    dept_counts = qs.values('student__department__code').annotate(total=Count('id')).order_by('-total')[:10]
    type_counts = qs.values('od_type').annotate(total=Count('id')).order_by('-total')[:10]
    delay_items = []
    for obj in qs.exclude(faculty_approved_at__isnull=True)[:300]:
        faculty_delay = (obj.faculty_approved_at - obj.created_at).total_seconds() / 3600 if obj.faculty_approved_at else None
        dean_delay = (obj.dean_approved_at - obj.faculty_approved_at).total_seconds() / 3600 if obj.dean_approved_at and obj.faculty_approved_at else None
        delay_items.append({'obj': obj, 'faculty_delay': faculty_delay, 'dean_delay': dean_delay})
    return render(request, 'reports/analytics.html', {
        'status_counts': status_counts,
        'dept_counts': dept_counts,
        'type_counts': type_counts,
        'total': total,
        'delay_items': delay_items[:40],
    })
