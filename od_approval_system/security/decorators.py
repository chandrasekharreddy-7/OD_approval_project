from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from accounts.models import UserRole


def role_required(*roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.is_superuser or request.user.role in roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('accounts:redirect')
        return _wrapped
    return decorator


student_required = role_required(UserRole.STUDENT)
faculty_required = role_required(UserRole.FACULTY)
dean_required = role_required(UserRole.DEAN)
admin_required = role_required(UserRole.ADMIN)
