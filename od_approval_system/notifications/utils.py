from .models import Notification
from .services import fanout_alert


def notify_user(user, title, message, url=''):
    if not user:
        return None
    notification = Notification.objects.create(user=user, title=title, message=message, url=url)
    try:
        fanout_alert(user, title, message)
    except Exception:
        # External alerts must never break the OD approval flow.
        pass
    return notification
