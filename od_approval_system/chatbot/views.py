import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from security.utils import create_audit_log
from .services import ask_openrouter


@require_POST
@csrf_protect
def chat(request):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'reply': 'Invalid chat request.'}, status=400)
    message = (payload.get('message') or '').strip()
    if not message:
        return JsonResponse({'ok': False, 'reply': 'Please type a question.'}, status=400)
    if len(message) > 2000:
        return JsonResponse({'ok': False, 'reply': 'Please keep the question under 2000 characters.'}, status=400)
    reply = ask_openrouter(request.user, message)
    if getattr(request.user, 'is_authenticated', False):
        create_audit_log(request, 'AI_CHATBOT_USED', 'Chatbot', '', message[:180])
    return JsonResponse({'ok': True, 'reply': reply})
