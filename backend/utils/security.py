import hmac
import secrets

from flask import request, session


def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_urlsafe(32)
        session.permanent = True
    return session['_csrf_token']


def validate_csrf_token():
    expected = session.get('_csrf_token')
    supplied = request.headers.get('X-CSRF-Token')
    if not expected or not supplied:
        return False
    return hmac.compare_digest(expected, supplied)


def password_meets_policy(password, username, min_length=12, max_length=128):
    if not isinstance(password, str) or not min_length <= len(password) <= max_length:
        return False
    if username and username.casefold() in password.casefold():
        return False

    categories = [
        any(character.islower() for character in password),
        any(character.isupper() for character in password),
        any(character.isdigit() for character in password),
        any(not character.isalnum() for character in password),
    ]
    return sum(categories) >= 3
