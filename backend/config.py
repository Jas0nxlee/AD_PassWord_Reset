import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv


if getattr(sys, 'frozen', False):
    executable_path = Path(sys.executable).resolve()
    if executable_path.parent.name == 'MacOS' and executable_path.parent.parent.name == 'Contents':
        APPLICATION_PATH = executable_path.parents[3]
    else:
        APPLICATION_PATH = executable_path.parent
else:
    APPLICATION_PATH = Path(__file__).resolve().parent.parent

load_dotenv(APPLICATION_PATH / '.env')


def _as_bool(name, default=False):
    value = os.environ.get(name, str(default))
    return value.strip().lower() in {'true', '1', 'yes', 'on'}


def _as_int(name, default):
    value = os.environ.get(name, str(default))
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f'{name} must be an integer') from exc


class Config:
    """从环境变量加载并验证应用配置。"""

    SECRET_KEY = os.environ.get('SECRET_KEY')
    FLASK_DEBUG = _as_bool('FLASK_DEBUG', False)
    MAX_CONTENT_LENGTH = _as_int('MAX_CONTENT_LENGTH', 16 * 1024)

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = _as_bool('COOKIE_SECURE', False)
    SESSION_COOKIE_SAMESITE = 'Strict'
    PERMANENT_SESSION_LIFETIME = _as_int('SESSION_LIFETIME_SECONDS', 1800)
    CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE

    LDAP_SERVER = os.environ.get('LDAP_SERVER')
    LDAP_PORT = _as_int('LDAP_PORT', 636)
    LDAP_USE_SSL = _as_bool('LDAP_USE_SSL', True)
    LDAP_VERIFY_CERT = _as_bool('LDAP_VERIFY_CERT', True)
    LDAP_CA_CERT_PATH = os.environ.get('LDAP_CA_CERT_PATH') or None
    LDAP_CONNECT_TIMEOUT = _as_int('LDAP_CONNECT_TIMEOUT', 5)
    LDAP_RECEIVE_TIMEOUT = _as_int('LDAP_RECEIVE_TIMEOUT', 10)
    LDAP_BASE_DN = os.environ.get('LDAP_BASE_DN')
    LDAP_USER = os.environ.get('LDAP_USER')
    LDAP_PASSWORD = os.environ.get('LDAP_PASSWORD')
    LDAP_DOMAIN = os.environ.get('LDAP_DOMAIN')
    LDAP_AUTH_MODE = os.environ.get('LDAP_AUTH_MODE', 'NTLM').upper()
    LDAP_COMPATIBILITY_MODE = _as_bool('LDAP_COMPATIBILITY_MODE', False)
    LDAP_CERT_SHA256 = os.environ.get('LDAP_CERT_SHA256', '').replace(':', '').strip().lower()

    SMTP_SERVER = os.environ.get('SMTP_SERVER')
    SMTP_PORT = _as_int('SMTP_PORT', 465)
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    SMTP_USE_SSL = _as_bool('SMTP_USE_SSL', SMTP_PORT == 465)
    SMTP_VERIFY_CERT = _as_bool('SMTP_VERIFY_CERT', True)
    SMTP_CA_CERT_PATH = os.environ.get('SMTP_CA_CERT_PATH') or None
    SMTP_TIMEOUT = _as_int('SMTP_TIMEOUT', 10)
    EMAIL_ASYNC = _as_bool('EMAIL_ASYNC', True)
    EMAIL_WORKERS = _as_int('EMAIL_WORKERS', 2)
    EMAIL_QUEUE_LIMIT = _as_int('EMAIL_QUEUE_LIMIT', 100)

    SERVER_HOST = os.environ.get('SERVER_HOST', '127.0.0.1')
    SERVER_PORT = _as_int('SERVER_PORT', 5002)
    OPEN_BROWSER = _as_bool('OPEN_BROWSER', True)
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')
    LOG_DIR = os.environ.get('LOG_DIR', str(APPLICATION_PATH / 'logs'))

    VERIFICATION_CODE_TTL = _as_int('VERIFICATION_CODE_TTL', 300)
    VERIFICATION_CODE_COOLDOWN = _as_int('VERIFICATION_CODE_COOLDOWN', 60)
    VERIFICATION_MAX_ATTEMPTS = _as_int('VERIFICATION_MAX_ATTEMPTS', 5)
    RESET_TOKEN_TTL = _as_int('RESET_TOKEN_TTL', 600)
    PASSWORD_MIN_LENGTH = _as_int('PASSWORD_MIN_LENGTH', 12)
    PASSWORD_MAX_LENGTH = _as_int('PASSWORD_MAX_LENGTH', 128)

    @classmethod
    def validate(cls):
        required = [
            'SECRET_KEY',
            'LDAP_SERVER',
            'LDAP_BASE_DN',
            'LDAP_DOMAIN',
            'LDAP_USER',
            'LDAP_PASSWORD',
            'SMTP_SERVER',
            'SMTP_USERNAME',
            'SMTP_PASSWORD',
        ]
        missing = [name for name in required if not getattr(cls, name, None)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        if len(cls.SECRET_KEY) < 32 or cls.SECRET_KEY.startswith('change-this'):
            raise ValueError('SECRET_KEY must be a strong random value of at least 32 characters')
        if not cls.LDAP_USE_SSL:
            raise ValueError('LDAP_USE_SSL must be enabled')
        if not cls.LDAP_VERIFY_CERT:
            raise ValueError('LDAP_VERIFY_CERT must be enabled')
        if cls.LDAP_AUTH_MODE not in {'NTLM', 'SIMPLE'}:
            raise ValueError('LDAP_AUTH_MODE must be NTLM or SIMPLE')
        if cls.LDAP_COMPATIBILITY_MODE and not re.fullmatch(r'[0-9a-f]{64}', cls.LDAP_CERT_SHA256):
            raise ValueError('LDAP_CERT_SHA256 must be a 64-character SHA-256 fingerprint in compatibility mode')
        if not cls.SMTP_VERIFY_CERT:
            raise ValueError('SMTP_VERIFY_CERT must be enabled')
        if cls.EMAIL_WORKERS < 1 or cls.EMAIL_QUEUE_LIMIT < cls.EMAIL_WORKERS:
            raise ValueError('EMAIL_QUEUE_LIMIT must be greater than or equal to EMAIL_WORKERS')
        if cls.PASSWORD_MIN_LENGTH < 12:
            raise ValueError('PASSWORD_MIN_LENGTH must be at least 12')
        if cls.PASSWORD_MAX_LENGTH < cls.PASSWORD_MIN_LENGTH:
            raise ValueError('PASSWORD_MAX_LENGTH must not be smaller than PASSWORD_MIN_LENGTH')

        loopback_hosts = {'127.0.0.1', 'localhost', '::1'}
        if cls.SERVER_HOST not in loopback_hosts and not cls.SESSION_COOKIE_SECURE:
            raise ValueError('COOKIE_SECURE must be enabled when SERVER_HOST is not loopback')

        for name in ('LDAP_CA_CERT_PATH', 'SMTP_CA_CERT_PATH'):
            path = getattr(cls, name)
            if path and not Path(path).is_file():
                raise ValueError(f'{name} does not point to a readable file')
