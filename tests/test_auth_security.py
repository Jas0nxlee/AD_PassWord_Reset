import importlib
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / 'backend'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

REQUIRED_ENV = {
    'LDAP_SERVER': 'ldaps://example.com',
    'LDAP_BASE_DN': 'dc=example,dc=com',
    'LDAP_USER': 'svc_reset@example.com',
    'LDAP_PASSWORD': 'secret',
    'SMTP_SERVER': 'smtp.example.com',
    'SMTP_USERNAME': 'noreply@example.com',
    'SMTP_PASSWORD': 'secret',
    'SERVER_IP': '127.0.0.1',
    'SECRET_KEY': 'test-secret-key',
}


class DummyAttr:
    def __init__(self, value):
        self.value = value


class DummyUser:
    def __init__(self, email='alice@example.com', dn='CN=Alice,OU=Users,DC=example,DC=com'):
        self.mail = DummyAttr(email)
        self.distinguishedName = DummyAttr(dn)


@pytest.fixture
def app_client(monkeypatch):
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)

    for module_name in ['config', 'services.verification_service', 'routes.auth', 'app']:
        if module_name in sys.modules:
            del sys.modules[module_name]

    config = importlib.import_module('config')
    verification_module = importlib.import_module('services.verification_service')
    routes_auth = importlib.import_module('routes.auth')
    app_module = importlib.import_module('app')

    importlib.reload(config)
    importlib.reload(verification_module)
    importlib.reload(routes_auth)
    importlib.reload(app_module)

    verification_module.verification_service.codes.clear()

    application = app_module.create_app()
    application.config['TESTING'] = True
    client = application.test_client()

    response = client.get('/health')
    csrf_token = None
    for header in response.headers.getlist('Set-Cookie'):
        if header.startswith('csrf_token='):
            csrf_token = header.split('csrf_token=')[1].split(';')[0]
            break

    assert csrf_token, 'Expected csrf_token cookie to be set'
    return application, client, csrf_token, verification_module.verification_service


def test_verify_user_masks_email(app_client):
    application, client, csrf_token, _ = app_client
    headers = {'X-CSRF-Token': csrf_token}

    with patch.object(application.ldap_service, 'search_user', return_value=DummyUser('alice@example.com')):
        response = client.post('/api/verify-user', json={'username': 'alice'}, headers=headers)

    assert response.status_code == 200
    data = response.get_json()
    assert data['masked_email'] == 'a***e@example.com'
    assert 'alice@example.com' not in str(data)


def test_send_code_requires_only_username_and_enforces_cooldown(app_client):
    application, client, csrf_token, _ = app_client
    headers = {'X-CSRF-Token': csrf_token}

    search_patch = patch.object(application.ldap_service, 'search_user', return_value=DummyUser('alice@example.com'))
    mail_patch = patch('routes.auth.email_service.send_email', return_value=True)
    with search_patch:
        with mail_patch:
            first = client.post('/api/send-code', json={'username': 'alice'}, headers=headers)
            second = client.post('/api/send-code', json={'username': 'alice'}, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.get_json()['error']


def test_verify_code_expires_after_max_attempts(app_client):
    application, client, csrf_token, verification_service = app_client
    headers = {'X-CSRF-Token': csrf_token}

    search_patch = patch.object(application.ldap_service, 'search_user', return_value=DummyUser('alice@example.com'))
    mail_patch = patch('routes.auth.email_service.send_email', return_value=True)
    with search_patch:
        with mail_patch:
            sent = client.post('/api/send-code', json={'username': 'alice'}, headers=headers)
            assert sent.status_code == 200

            last_response = None
            for _ in range(5):
                last_response = client.post('/api/verify-code', json={'username': 'alice', 'code': '000000'}, headers=headers)

    assert last_response is not None
    assert last_response.status_code == 400
    assert last_response.get_json()['error'] == 'Verification code has expired. Please request a new code.'
    assert 'alice' not in verification_service.codes


def test_verify_code_returns_token_for_correct_code(app_client):
    application, client, csrf_token, verification_service = app_client
    headers = {'X-CSRF-Token': csrf_token}

    search_patch = patch.object(application.ldap_service, 'search_user', return_value=DummyUser('alice@example.com'))
    mail_patch = patch('routes.auth.email_service.send_email', return_value=True)
    with search_patch:
        with mail_patch:
            sent = client.post('/api/send-code', json={'username': 'alice'}, headers=headers)
            assert sent.status_code == 200

            code = verification_service.codes['alice']['code']
            verified = client.post('/api/verify-code', json={'username': 'alice', 'code': code}, headers=headers)

    assert verified.status_code == 200
    data = verified.get_json()
    assert data['message'] == 'Code verified successfully'
    assert data['token']


def test_config_validate_raises_when_required_env_missing(monkeypatch):
    for key in REQUIRED_ENV:
        monkeypatch.delenv(key, raising=False)

    module_name = 'config'
    if module_name in sys.modules:
        del sys.modules[module_name]

    with patch('os.path.exists', return_value=False), patch('dotenv.load_dotenv', return_value=False):
        with pytest.raises(ValueError):
            importlib.import_module(module_name)
