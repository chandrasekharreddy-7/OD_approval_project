import json
import urllib.parse
import urllib.request
from django.conf import settings
from django.core.mail import send_mail
from security.utils import create_audit_log


def send_email_alert(user, title, message):
    if not getattr(settings, 'EMAIL_NOTIFICATIONS_ENABLED', False) or not getattr(user, 'email', ''):
        return False
    try:
        send_mail(title, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
        return True
    except Exception:
        return False


def send_sms_alert(user, message):
    if not getattr(settings, 'SMS_NOTIFICATIONS_ENABLED', False) or not getattr(settings, 'FAST2SMS_API_KEY', ''):
        return False
    mobile = getattr(user, 'mobile', '')
    if not mobile:
        return False
    data = urllib.parse.urlencode({
        'authorization': settings.FAST2SMS_API_KEY,
        'route': 'q',
        'message': message[:300],
        'language': 'english',
        'flash': '0',
        'numbers': mobile,
    }).encode()
    req = urllib.request.Request('https://www.fast2sms.com/dev/bulkV2', data=data, method='POST')
    try:
        urllib.request.urlopen(req, timeout=10).read()
        return True
    except Exception:
        return False


def send_whatsapp_alert(user, message):
    # Placeholder-safe integration point: configure Twilio WhatsApp variables in .env.
    # It returns False when not configured, so local development never breaks.
    if not getattr(settings, 'WHATSAPP_NOTIFICATIONS_ENABLED', False):
        return False
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_WHATSAPP_FROM, getattr(user, 'mobile', '')]):
        return False
    # Twilio API call intentionally not hard-coded with secrets. Add twilio package for production if needed.
    return False


def fanout_alert(user, title, message):
    return {
        'email': send_email_alert(user, title, message),
        'sms': send_sms_alert(user, f'{title}: {message}'),
        'whatsapp': send_whatsapp_alert(user, f'{title}: {message}'),
    }
