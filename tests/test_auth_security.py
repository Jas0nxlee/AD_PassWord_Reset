import importlib
import hashlib
import re
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from ldap3.core.exceptions import LDAPException

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / 'backend'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

REQUIRED_ENV = {
    'LDAP_SERVER': 'example.com',
    'LDAP_PORT': '636',
    'LDAP_USE_SSL': 'true',
    'LDAP_VERIFY_CERT': 'true',
    'LDAP_COMPATIBILITY_MODE': 'false',
    'LDAP_CERT_SHA256': '',
    'LDAP_BASE_DN': 'dc=example,dc=com',
    'LDAP_DOMAIN': 'example.com',
    'LDAP_USER': 'svc_reset@example.com',
    'LDAP_PASSWORD': 'fake-test-password',
    'SMTP_SERVER': 'smtp.example.com',
    'SMTP_PORT': '465',
    'SMTP_USERNAME': 'noreply@example.com',
    'SMTP_PASSWORD': 'fake-test-password',
    'SECRET_KEY': 'test-secret-key-that-is-longer-than-32-bytes',
}


class DummyUser:
    def __init__(self, email='alice@example.com', dn='CN=Alice,OU=Users,DC=example,DC=com'):
        self.email = email
        self.distinguished_name = dn
        self.username = 'alice'


@pytest.fixture
def app_client(monkeypatch, tmp_path):
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv('LOG_DIR', str(tmp_path / 'logs'))
    monkeypatch.setenv('EMAIL_ASYNC', 'false')

    for module_name in [
        'config',
        'services.verification_service',
        'services.reset_token_service',
        'services.email_service',
        'services.ldap_service',
        'routes.auth',
        'app',
    ]:
        sys.modules.pop(module_name, None)

    app_module = importlib.import_module('app')
    application = app_module.create_app()
    application.config['TESTING'] = True
    client = application.test_client()

    response = client.get('/health')
    csrf_token = next(
        header.split('csrf_token=', 1)[1].split(';', 1)[0]
        for header in response.headers.getlist('Set-Cookie')
        if header.startswith('csrf_token=')
    )
    return application, client, csrf_token


def _headers(csrf_token):
    return {'X-CSRF-Token': csrf_token}


def _request_code(application, client, csrf_token, username='alice'):
    with (
        patch.object(application.ldap_service, 'search_user', return_value=DummyUser()),
        patch.object(application.email_service, 'send_email', return_value=True) as send_email,
    ):
        response = client.post('/api/send-code', json={'username': username}, headers=_headers(csrf_token))

    body = send_email.call_args.args[2]
    return response, re.search(r'\b(\d{6})\b', body).group(1)


def test_static_route_rejects_directory_traversal(app_client):
    _, client, _ = app_client
    response = client.get('/%2e%2e/%2e%2e/README.md')
    assert response.status_code == 404
    assert b'AD Password Reset Application' not in response.data


def test_verify_user_does_not_disclose_account_state(app_client):
    application, client, csrf_token = app_client
    with patch.object(application.ldap_service, 'search_user') as search_user:
        response = client.post('/api/verify-user', json={'username': 'alice'}, headers=_headers(csrf_token))
    assert response.status_code == 200
    assert response.get_json() == {
        'message': 'If the account is eligible, a verification code will be sent.'
    }
    search_user.assert_not_called()


def test_send_code_uses_generic_response_for_existing_and_missing_users(app_client):
    application, client, csrf_token = app_client
    generic_response = {'message': 'If the account is eligible, a verification code will be sent.'}
    with (
        patch.object(application.ldap_service, 'search_user', return_value=DummyUser()),
        patch.object(application.email_service, 'send_email', return_value=True),
    ):
        existing = client.post('/api/send-code', json={'username': 'alice'}, headers=_headers(csrf_token))
    with patch.object(application.ldap_service, 'search_user', return_value=None):
        missing = client.post('/api/send-code', json={'username': 'nobody'}, headers=_headers(csrf_token))
    assert existing.status_code == missing.status_code == 200
    assert existing.get_json() == missing.get_json() == generic_response


def test_email_failure_does_not_leave_cooldown_record(app_client):
    application, client, csrf_token = app_client
    with (
        patch.object(application.ldap_service, 'search_user', return_value=DummyUser()),
        patch.object(application.email_service, 'send_email', side_effect=[False, True]) as send_email,
    ):
        first = client.post('/api/send-code', json={'username': 'alice'}, headers=_headers(csrf_token))
        second = client.post('/api/send-code', json={'username': 'ALICE'}, headers=_headers(csrf_token))
    assert first.status_code == second.status_code == 200
    assert send_email.call_count == 2


def test_verification_code_expires_after_max_attempts(app_client):
    application, client, csrf_token = app_client
    sent, valid_code = _request_code(application, client, csrf_token)
    assert sent.status_code == 200
    wrong_code = '000000' if valid_code != '000000' else '111111'
    responses = [
        client.post(
            '/api/verify-code',
            json={'username': 'alice', 'code': wrong_code},
            headers=_headers(csrf_token),
        )
        for _ in range(5)
    ]
    assert responses[-1].status_code == 400
    assert responses[-1].get_json()['error'] == 'Verification code has expired. Please request a new code.'


def test_reset_token_is_single_use(app_client):
    application, client, csrf_token = app_client
    _, code = _request_code(application, client, csrf_token)
    verified = client.post(
        '/api/verify-code',
        json={'username': 'alice', 'code': code},
        headers=_headers(csrf_token),
    )
    token = verified.get_json()['token']
    with (
        patch.object(application.ldap_service, 'search_user', return_value=DummyUser()),
        patch.object(application.ldap_service, 'reset_password', return_value=True) as reset_password,
        patch.object(application.email_service, 'send_email', return_value=True),
    ):
        first = client.post(
            '/api/reset-password',
            json={'username': 'alice', 'new_password': 'A-secure-password-2026!', 'token': token},
            headers=_headers(csrf_token),
        )
        second = client.post(
            '/api/reset-password',
            json={'username': 'alice', 'new_password': 'Another-secure-password-2026!', 'token': token},
            headers=_headers(csrf_token),
        )
    assert first.status_code == 200
    assert second.status_code == 401
    assert reset_password.call_count == 1


def test_backend_rejects_weak_password_before_ldap_call(app_client):
    application, client, csrf_token = app_client
    _, code = _request_code(application, client, csrf_token)
    verified = client.post(
        '/api/verify-code',
        json={'username': 'alice', 'code': code},
        headers=_headers(csrf_token),
    )
    with patch.object(application.ldap_service, 'reset_password') as reset_password:
        response = client.post(
            '/api/reset-password',
            json={'username': 'alice', 'new_password': 'password', 'token': verified.get_json()['token']},
            headers=_headers(csrf_token),
        )
    assert response.status_code == 400
    reset_password.assert_not_called()


@pytest.mark.parametrize(
    ('content_type', 'body', 'expected_status'),
    [('application/json', '{', 400), ('text/plain', 'hello', 415)],
)
def test_invalid_request_preserves_http_status(app_client, content_type, body, expected_status):
    _, client, csrf_token = app_client
    response = client.post(
        '/api/verify-user',
        data=body,
        content_type=content_type,
        headers=_headers(csrf_token),
    )
    assert response.status_code == expected_status
    assert response.is_json


def test_config_rejects_missing_secret_and_insecure_ldap(monkeypatch):
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv('SECRET_KEY', '')
    sys.modules.pop('config', None)
    config_module = importlib.import_module('config')
    with pytest.raises(ValueError, match='SECRET_KEY'):
        config_module.Config.validate()
    monkeypatch.setenv('SECRET_KEY', REQUIRED_ENV['SECRET_KEY'])
    monkeypatch.setenv('LDAP_VERIFY_CERT', 'false')
    config_module = importlib.reload(config_module)
    with pytest.raises(ValueError, match='LDAP_VERIFY_CERT'):
        config_module.Config.validate()


def test_ldap_connection_is_fail_closed_and_verifies_certificate():
    ldap_module = importlib.import_module('services.ldap_service')
    service = ldap_module.LDAPService({
        'LDAP_SERVER': 'example.com',
        'LDAP_PORT': 636,
        'LDAP_BASE_DN': 'dc=example,dc=com',
        'LDAP_DOMAIN': 'example.com',
        'LDAP_USER': 'svc@example.com',
        'LDAP_PASSWORD': 'fake',
        'LDAP_AUTH_MODE': 'NTLM',
        'LDAP_CA_CERT_PATH': None,
        'LDAP_CONNECT_TIMEOUT': 5,
        'LDAP_RECEIVE_TIMEOUT': 10,
    })
    with (
        patch.object(ldap_module, 'Tls') as tls,
        patch.object(ldap_module, 'Server'),
        patch.object(ldap_module, 'Connection', side_effect=LDAPException('bind failed')) as connection,
        pytest.raises(LDAPException),
    ):
        service._create_connection()
    assert tls.call_args.kwargs['validate'] == ssl.CERT_REQUIRED
    assert connection.call_count == 1


def test_in_memory_reset_token_is_consumed_atomically():
    token_module = importlib.import_module('services.reset_token_service')
    service = token_module.ResetTokenService(ttl=60)
    token = service.issue('alice')

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: service.consume(token, 'ALICE'), range(2)))

    assert results.count(True) == 1
    assert results.count(False) == 1


def test_in_memory_code_cooldown_is_case_insensitive_and_atomic():
    verification_module = importlib.import_module('services.verification_service')
    service = verification_module.VerificationService(cooldown_time=60)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(service.begin_code, ['alice', 'ALICE']))

    assert sum(result['success'] for result in results) == 1


def test_smtp_uses_verified_tls_context():
    email_module = importlib.import_module('services.email_service')
    service = email_module.EmailService({
        'SMTP_SERVER': 'smtp.example.com',
        'SMTP_PORT': 465,
        'SMTP_USERNAME': 'noreply@example.com',
        'SMTP_PASSWORD': 'fake',
        'SMTP_USE_SSL': True,
        'SMTP_CA_CERT_PATH': None,
        'SMTP_TIMEOUT': 10,
    })
    tls_context = MagicMock()
    smtp_client = MagicMock()
    smtp_context_manager = MagicMock()
    smtp_context_manager.__enter__.return_value = smtp_client

    with (
        patch.object(email_module.ssl, 'create_default_context', return_value=tls_context) as create_context,
        patch.object(email_module.smtplib, 'SMTP_SSL', return_value=smtp_context_manager) as smtp_ssl,
    ):
        assert service.send_email('alice@example.com', 'subject', 'body') is True

    create_context.assert_called_once_with(cafile=None)
    smtp_ssl.assert_called_once_with('smtp.example.com', 465, timeout=10, context=tls_context)


def test_security_headers_and_cookie_flags_are_set(app_client):
    _, client, _ = app_client
    response = client.get('/health')

    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert "frame-ancestors 'none'" in response.headers['Content-Security-Policy']
    assert any(
        header.startswith('csrf_token=') and 'SameSite=Strict' in header
        for header in response.headers.getlist('Set-Cookie')
    )


def test_ldap_compatibility_mode_pins_certificate_before_bind():
    ldap_module = importlib.import_module('services.ldap_service')
    certificate = b'legacy-certificate'
    fingerprint = hashlib.sha256(certificate).hexdigest()
    service = ldap_module.LDAPService({
        'LDAP_SERVER': 'example.com',
        'LDAP_PORT': 636,
        'LDAP_BASE_DN': 'dc=example,dc=com',
        'LDAP_DOMAIN': 'example.com',
        'LDAP_USER': 'svc@example.com',
        'LDAP_PASSWORD': 'fake',
        'LDAP_AUTH_MODE': 'NTLM',
        'LDAP_CA_CERT_PATH': None,
        'LDAP_CONNECT_TIMEOUT': 5,
        'LDAP_RECEIVE_TIMEOUT': 10,
        'LDAP_COMPATIBILITY_MODE': True,
        'LDAP_CERT_SHA256': fingerprint,
    })
    connection = MagicMock()
    connection.closed = False
    connection.bind.return_value = True
    connection.socket.getpeercert.return_value = certificate

    with (
        patch.object(ldap_module, 'Tls') as tls,
        patch.object(ldap_module, 'Server'),
        patch.object(ldap_module, 'Connection', return_value=connection),
    ):
        assert service._create_connection() is connection

    assert tls.call_args.kwargs['validate'] == ssl.CERT_NONE
    assert tls.call_args.kwargs['ciphers'] == 'DEFAULT:@SECLEVEL=0'
    connection.open.assert_called_once_with()
    connection.socket.getpeercert.assert_called_once_with(binary_form=True)
    connection.bind.assert_called_once_with()


def test_ldap_compatibility_mode_rejects_unpinned_certificate_before_bind():
    ldap_module = importlib.import_module('services.ldap_service')
    service = ldap_module.LDAPService({
        'LDAP_SERVER': 'example.com',
        'LDAP_PORT': 636,
        'LDAP_BASE_DN': 'dc=example,dc=com',
        'LDAP_DOMAIN': 'example.com',
        'LDAP_USER': 'svc@example.com',
        'LDAP_PASSWORD': 'fake',
        'LDAP_AUTH_MODE': 'NTLM',
        'LDAP_CA_CERT_PATH': None,
        'LDAP_CONNECT_TIMEOUT': 5,
        'LDAP_RECEIVE_TIMEOUT': 10,
        'LDAP_COMPATIBILITY_MODE': True,
        'LDAP_CERT_SHA256': '0' * 64,
    })
    connection = MagicMock()
    connection.closed = False
    connection.socket.getpeercert.return_value = b'unexpected-certificate'

    with (
        patch.object(ldap_module, 'Tls'),
        patch.object(ldap_module, 'Server'),
        patch.object(ldap_module, 'Connection', return_value=connection),
        pytest.raises(LDAPException, match='fingerprint'),
    ):
        service._create_connection()

    connection.bind.assert_not_called()
