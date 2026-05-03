from io import BytesIO
import hashlib
import qrcode
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def certificate_hash(od_request):
    raw = '|'.join([
        str(od_request.verification_id),
        od_request.student.roll_number,
        od_request.event_title,
        str(od_request.from_date),
        str(od_request.to_date),
        od_request.status,
    ])
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24].upper()


def _draw_signature(pdf, user, x, y, label):
    pdf.setFont('Helvetica-Bold', 9)
    pdf.drawString(x, y + 20 * mm, label)
    profile = getattr(user, 'faculty_profile', None) or getattr(user, 'dean_profile', None) if user else None
    if profile and getattr(profile, 'signature_image', None):
        try:
            pdf.drawImage(ImageReader(profile.signature_image.path), x, y + 4 * mm, 42 * mm, 14 * mm, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    pdf.line(x, y, x + 55 * mm, y)
    pdf.setFont('Helvetica', 8)
    pdf.drawString(x, y - 4 * mm, user.get_full_name() if user else '-')


def build_od_letter_response(request, od_request):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 22 * mm
    pdf.setFont('Helvetica-Bold', 18)
    pdf.drawCentredString(width / 2, y, 'SAI UNIVERSITY')
    y -= 8 * mm
    pdf.setFont('Helvetica', 10)
    pdf.drawCentredString(width / 2, y, 'Digitally Verified On-Duty Approval Letter')
    y -= 11 * mm
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(20 * mm, y, 'Verification ID:')
    pdf.setFont('Helvetica', 11)
    pdf.drawString(58 * mm, y, str(od_request.verification_id))
    y -= 7 * mm
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(20 * mm, y, 'Digital Hash:')
    pdf.setFont('Helvetica', 11)
    pdf.drawString(58 * mm, y, certificate_hash(od_request))
    y -= 11 * mm

    fields = [
        ('Student Name', od_request.student.user.get_full_name()),
        ('Roll Number', od_request.student.roll_number),
        ('Department', od_request.student.department.name),
        ('School', od_request.student.school.name),
        ('OD Type', od_request.get_od_type_display()),
        ('Event Title', od_request.event_title),
        ('Place', od_request.place),
        ('From Date', od_request.from_date.strftime('%d-%m-%Y')),
        ('To Date', od_request.to_date.strftime('%d-%m-%Y')),
        ('Approved by Faculty', od_request.faculty_approved_by.get_full_name() if od_request.faculty_approved_by else '-'),
        ('Approved by Dean', od_request.dean_approved_by.get_full_name() if od_request.dean_approved_by else '-'),
        ('Approval Date', od_request.dean_approved_at.strftime('%d-%m-%Y %I:%M %p') if od_request.dean_approved_at else '-'),
    ]
    for label, value in fields:
        pdf.setFont('Helvetica-Bold', 10)
        pdf.drawString(20 * mm, y, f'{label}:')
        pdf.setFont('Helvetica', 10)
        pdf.drawString(64 * mm, y, str(value)[:82])
        y -= 7 * mm

    y -= 4 * mm
    pdf.setFont('Helvetica', 9)
    text = pdf.beginText(20 * mm, y)
    text.textLine('This OD letter is system-generated and protected with QR verification, audit trail, and digital hash.')
    text.textLine('Scan the QR code or enter the verification ID on the OD verification page to confirm authenticity.')
    pdf.drawText(text)

    verify_url = request.build_absolute_uri(f'/od/verify/{od_request.verification_id}/')
    qr = qrcode.make(verify_url)
    qr_buffer = BytesIO()
    qr.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    pdf.drawImage(ImageReader(qr_buffer), 20 * mm, 32 * mm, 34 * mm, 34 * mm)
    pdf.setFont('Helvetica-Bold', 9)
    pdf.drawString(58 * mm, 57 * mm, 'Verification')
    pdf.setFont('Helvetica', 8)
    pdf.drawString(58 * mm, 52 * mm, verify_url[:105])
    pdf.drawString(58 * mm, 47 * mm, f'Hash: {certificate_hash(od_request)}')

    _draw_signature(pdf, od_request.faculty_approved_by, 20 * mm, 18 * mm, 'Faculty / Mentor Signature')
    _draw_signature(pdf, od_request.dean_approved_by, 122 * mm, 18 * mm, 'Dean Signature')

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="OD_Letter_{od_request.student.roll_number}_{od_request.pk}.pdf"'
    return response
