import os
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from .models import ODRequest, ODStatus, UploadedDocument
from accounts.models import UserRole
from security.utils import create_audit_log


def verify_od(request, verification_id):
    od_request = get_object_or_404(ODRequest.objects.select_related('student__user', 'student__school', 'student__department'), verification_id=verification_id)
    valid = od_request.status == ODStatus.DEAN_APPROVED
    return render(request, 'od/verify.html', {'od_request': od_request, 'valid': valid})


def _can_access_document(user, od_request):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.role == UserRole.ADMIN:
        return True
    if user.role == UserRole.STUDENT:
        return hasattr(user, 'student_profile') and od_request.student_id == user.student_profile.id
    if user.role == UserRole.FACULTY:
        return hasattr(user, 'faculty_profile') and od_request.student.mentor_id == user.id
    if user.role == UserRole.DEAN:
        return hasattr(user, 'dean_profile') and od_request.student.school_id == user.dean_profile.school_id
    return False


def download_document(request, document_id):
    document = get_object_or_404(UploadedDocument.objects.select_related('od_request__student__user', 'od_request__student__school'), pk=document_id)
    if not _can_access_document(request.user, document.od_request):
        return HttpResponseForbidden('You do not have permission to access this document.')
    if not document.file or not os.path.exists(document.file.path):
        raise Http404('Document file not found.')
    create_audit_log(request, 'OD_DOCUMENT_VIEWED', 'UploadedDocument', document.pk, f'Viewed {document.original_filename}')
    return FileResponse(open(document.file.path, 'rb'), as_attachment=False, filename=document.original_filename)
