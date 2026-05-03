import json
import os
import urllib.error
import urllib.request
from django.conf import settings

SYSTEM_PROMPT = """
You are SAI University OD Assistant inside the University OD Approval System.
Answer only questions about OD workflow, student applications, approvals, reports,
roles, uploaded proof, QR verification, rules, and safe system usage. Do not reveal
secrets, API keys, database passwords, or private details of other users. If the
question asks for an action, guide the user to the correct page based on their role.
Keep answers short, clear, and beginner-friendly.
""".strip()


def build_role_context(user):
    if not getattr(user, 'is_authenticated', False):
        return 'Visitor: can view home/login and verify OD QR only.'
    role = getattr(user, 'role', 'UNKNOWN')
    pieces = [f'Current user role: {role}.']
    if role == 'STUDENT' and hasattr(user, 'student_profile'):
        p = user.student_profile
        pieces.append(f'Student roll: {p.roll_number}; department: {p.department.code}; school: {p.school.code}.')
    elif role == 'FACULTY' and hasattr(user, 'faculty_profile'):
        p = user.faculty_profile
        pieces.append(f'Faculty department: {p.department.code}; school: {p.school.code}.')
    elif role == 'DEAN' and hasattr(user, 'dean_profile'):
        p = user.dean_profile
        pieces.append(f'Dean school: {p.school.code}.')
    return ' '.join(pieces)


def ask_openrouter(user, message):
    api_key = getattr(settings, 'OPENROUTER_API_KEY', '') or os.getenv('OPENROUTER_API_KEY', '')
    model = getattr(settings, 'OPENROUTER_MODEL', 'openrouter/free') or 'openrouter/free'
    if not api_key or api_key.startswith('PASTE_'):
        return (
            'AI assistant is installed, but OPENROUTER_API_KEY is not configured. '
            'Add your key in .env and restart the server.'
        )

    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'system', 'content': build_role_context(user)},
            {'role': 'user', 'content': str(message)[:2000]},
        ],
        'temperature': 0.2,
        'max_tokens': 350,
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        'https://openrouter.ai/api/v1/chat/completions',
        data=data,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000'),
            'X-Title': 'SAI University',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            body = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode('utf-8')[:400]
        except Exception:
            detail = str(exc)
        return f'OpenRouter request failed: {detail}'
    except Exception as exc:
        return f'AI assistant could not connect right now: {exc}'

    try:
        return body['choices'][0]['message']['content'].strip()
    except Exception:
        return 'AI assistant received an unexpected response. Please check OPENROUTER_MODEL in .env.'
