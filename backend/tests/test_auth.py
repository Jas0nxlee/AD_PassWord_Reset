import pytest
from flask import Flask, jsonify, request
import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from routes.auth import auth_bp
from utils.security import generate_token
from unittest.mock import MagicMock

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret'
    app.config['TESTING'] = True
    app.ldap_service = MagicMock()
    app.register_blueprint(auth_bp, url_prefix='/api')
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def mock_ldap(app):
    return app.ldap_service

@pytest.fixture
def mock_email(mocker):
    return mocker.patch('routes.auth.email_service')

@pytest.fixture
def mock_verify(mocker):
    return mocker.patch('routes.auth.verification_service')

@pytest.fixture
def mock_audit(mocker):
    return mocker.patch('routes.auth.audit_log')

def test_verify_user_missing_username(client):
    res = client.post('/api/verify-user', json={})
    assert res.status_code == 400

def test_verify_user_not_found(client, mock_ldap):
    mock_ldap.search_user.return_value = None
    res = client.post('/api/verify-user', json={"username": "test"})
    assert res.status_code == 404

def test_verify_user_no_email(client, mock_ldap):
    class DummyUser:
        pass
    mock_ldap.search_user.return_value = DummyUser()
    res = client.post('/api/verify-user', json={"username": "test"})
    assert res.status_code == 404

def test_verify_user_success(client, mock_ldap):
    class DummyMail:
        value = "test@test.com"
    class DummyUser:
        mail = DummyMail()
    mock_ldap.search_user.return_value = DummyUser()
    res = client.post('/api/verify-user', json={"username": "test"})
    assert res.status_code == 200
    assert res.get_json()['email'] == "test@test.com"

def test_send_code_missing_username(client):
    res = client.post('/api/send-code', json={})
    assert res.status_code == 400

def test_send_code_user_not_found(client, mock_ldap):
    mock_ldap.search_user.return_value = None
    res = client.post('/api/send-code', json={"username": "test"})
    assert res.status_code == 404

def test_send_code_no_email(client, mock_ldap):
    class DummyUser:
        pass
    mock_ldap.search_user.return_value = DummyUser()
    res = client.post('/api/send-code', json={"username": "test"})
    assert res.status_code == 404

def test_send_code_email_fail(client, mock_ldap, mock_verify, mock_email):
    class DummyMail:
        value = "test@test.com"
    class DummyUser:
        mail = DummyMail()
    mock_ldap.search_user.return_value = DummyUser()
    mock_verify.generate_code.return_value = "123456"
    mock_email.send_email.return_value = False

    res = client.post('/api/send-code', json={"username": "test"})
    assert res.status_code == 500

def test_send_code_success(client, mock_ldap, mock_verify, mock_email):
    class DummyMail:
        value = "test@test.com"
    class DummyUser:
        mail = DummyMail()
    mock_ldap.search_user.return_value = DummyUser()
    mock_verify.generate_code.return_value = "123456"
    mock_email.send_email.return_value = True

    res = client.post('/api/send-code', json={"username": "test"})
    assert res.status_code == 200

def test_verify_code_missing_data(client):
    res = client.post('/api/verify-code', json={})
    assert res.status_code == 400

def test_verify_code_invalid(client, mock_verify):
    mock_verify.verify_code.return_value = False
    res = client.post('/api/verify-code', json={"username": "test", "code": "123"})
    assert res.status_code == 400

def test_verify_code_success(app, client, mock_verify):
    mock_verify.verify_code.return_value = True
    res = client.post('/api/verify-code', json={"username": "test", "code": "123"})
    assert res.status_code == 200
    assert 'token' in res.get_json()

def test_reset_password_missing_data(client):
    res = client.post('/api/reset-password', json={})
    assert res.status_code == 400

def test_reset_password_invalid_token(app, client):
    with app.app_context():
        # Valid token but wrong username
        token = generate_token({'username': 'other'})
        res = client.post('/api/reset-password', json={"username": "test", "new_password": "p", "token": token})
        assert res.status_code == 401

def test_reset_password_user_not_found(app, client, mock_ldap):
    with app.app_context():
        token = generate_token({'username': 'test'})
        mock_ldap.search_user.return_value = None
        res = client.post('/api/reset-password', json={"username": "test", "new_password": "p", "token": token})
        assert res.status_code == 404

def test_reset_password_fail(app, client, mock_ldap, mock_audit):
    with app.app_context():
        token = generate_token({'username': 'test'})
        class DummyDN:
            value = "cn=test"
        class DummyUser:
            distinguishedName = DummyDN()
        mock_ldap.search_user.return_value = DummyUser()
        mock_ldap.reset_password.return_value = False

        res = client.post('/api/reset-password', json={"username": "test", "new_password": "p", "token": token})
        assert res.status_code == 500
        mock_audit.assert_called_with('PASSWORD_RESET_FAILURE', 'test', {'user_dn': 'cn=test', 'error': 'LDAP password reset failed'})

def test_reset_password_success(app, client, mock_ldap, mock_audit):
    with app.app_context():
        token = generate_token({'username': 'test'})
        class DummyDN:
            value = "cn=test"
        class DummyUser:
            distinguishedName = DummyDN()
        mock_ldap.search_user.return_value = DummyUser()
        mock_ldap.reset_password.return_value = True

        res = client.post('/api/reset-password', json={"username": "test", "new_password": "p", "token": token})
        assert res.status_code == 200
        mock_audit.assert_called_with('PASSWORD_RESET_SUCCESS', 'test', {'user_dn': 'cn=test'})
