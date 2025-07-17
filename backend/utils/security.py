import itsdangerous
from flask import current_app, request, session
from markupsafe import escape

def generate_token(data):
    serializer = itsdangerous.URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(data)

def verify_token(token, max_age=3600):
    serializer = itsdangerous.URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = serializer.loads(token, max_age=max_age)
    except (itsdangerous.SignatureExpired, itsdangerous.BadTimeSignature, itsdangerous.BadSignature):
        return None
    return data

def sanitize_input(data):
    if isinstance(data, str):
        return escape(data)
    if isinstance(data, list):
        return [sanitize_input(item) for item in data]
    if isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    return data

def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = generate_token('csrf')
    return session['_csrf_token']

def validate_csrf_token():
    token = session.get('_csrf_token') # Use get instead of pop to avoid removing the token
    header_token = request.headers.get('X-CSRF-Token')
    if not token or token != header_token:
        return False
    return True