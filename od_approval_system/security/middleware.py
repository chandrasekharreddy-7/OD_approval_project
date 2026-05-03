from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

from .utils import get_client_ip


class RateLimitMiddleware:
    """
    Lightweight per-IP/per-user rate limiting using Django cache.

    Defaults are safe for a university intranet and can be changed through .env:
    RATE_LIMIT_GENERAL_PER_MINUTE, RATE_LIMIT_POST_PER_MINUTE,
    RATE_LIMIT_LOGIN_PER_MINUTE, RATE_LIMIT_UPLOAD_PER_5_MINUTES.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, 'RATE_LIMIT_ENABLED', True) and self._should_limit(request):
            limit, window, bucket = self._policy(request)
            if self._is_limited(request, limit, window, bucket):
                return HttpResponse('Too many requests. Please wait and try again.', status=429)
        return self.get_response(request)

    def _should_limit(self, request):
        path = request.path_info or ''
        if path.startswith(('/static/', '/media/')):
            return False
        return True

    def _policy(self, request):
        path = request.path_info or ''
        method = request.method.upper()
        if path.startswith('/accounts/login/') and method == 'POST':
            return getattr(settings, 'RATE_LIMIT_LOGIN_PER_MINUTE', 8), 60, 'login'
        if 'upload' in path or 'import-students' in path:
            return getattr(settings, 'RATE_LIMIT_UPLOAD_PER_5_MINUTES', 10), 300, 'upload'
        if method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            return getattr(settings, 'RATE_LIMIT_POST_PER_MINUTE', 35), 60, 'write'
        return getattr(settings, 'RATE_LIMIT_GENERAL_PER_MINUTE', 180), 60, 'read'

    def _identity(self, request):
        if getattr(request, 'user', None) and request.user.is_authenticated:
            return f'user:{request.user.pk}'
        return f'ip:{get_client_ip(request) or "unknown"}'

    def _is_limited(self, request, limit, window, bucket):
        key = f'rl:{bucket}:{self._identity(request)}'
        count = cache.get(key, 0)
        if count >= limit:
            return True
        if count == 0:
            cache.set(key, 1, timeout=window)
        else:
            cache.incr(key)
        return False


class ForcePasswordChangeMiddleware:
    """Redirect users with temporary passwords to the password-change page."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        path = request.path_info or ''
        allowed = (
            path.startswith('/accounts/change-password/') or
            path.startswith('/accounts/logout/') or
            path.startswith('/static/') or
            path.startswith('/media/')
        )
        if user and user.is_authenticated and getattr(user, 'must_change_password', False) and not allowed:
            from django.shortcuts import redirect
            return redirect('accounts:password_change_required')
        return self.get_response(request)
