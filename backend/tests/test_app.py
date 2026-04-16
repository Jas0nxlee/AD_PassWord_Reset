import pytest
from unittest.mock import patch, MagicMock
import os
import sys

# Ensure backend is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from werkzeug.exceptions import NotFound, InternalServerError

@pytest.fixture
def mock_ldap_service(mocker):
    return mocker.patch('app.LDAPService')

@pytest.fixture
def app(mock_ldap_service):
    app = create_app()
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_health_check(client):
    res = client.get('/health')
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok"}

def test_serve_frontend(client, mocker):
    mocker.patch('app.os.path.exists', return_value=True)
    mocker.patch('app.send_file', return_value="index_content")

    res = client.get('/')
    assert res.data == b"index_content"

def test_serve_static_existing_file(client, mocker):
    mocker.patch('app.os.path.exists', return_value=True)
    mocker.patch('app.send_file', return_value="static_content")

    res = client.get('/assets/test.css')
    assert res.data == b"static_content"

def test_serve_static_fallback(client, mocker):
    mocker.patch('app.os.path.exists', return_value=False)
    mocker.patch('app.send_file', return_value="index_content")

    res = client.get('/some-random-route')
    assert res.data == b"index_content"

def test_404_error_api(app):
    with app.test_request_context('/api/not-found'):
        res = app.error_handler_spec[None][404][NotFound](NotFound())
        assert res[0].get_json() == {"error": "Not Found"}
        assert res[1] == 404

def test_404_handler_non_api(app, mocker):
    with app.test_request_context('/not-api'):
        mocker.patch('app.send_file', return_value="index_content")
        res = app.error_handler_spec[None][404][NotFound](NotFound())
        assert res == "index_content"

def test_500_handler(client, mocker):
    @client.application.route('/trigger-500')
    def trigger_500():
        raise Exception("500")

    res = client.get('/trigger-500')
    assert res.status_code == 500
    assert res.get_json() == {"error": "An unexpected error occurred. Please try again later."} # middleware captures it!

def test_500_handler_direct(app):
    with app.test_request_context('/'):
        res = app.error_handler_spec[None][500][InternalServerError](InternalServerError())
        assert res[0].get_json() == {"error": "Internal Server Error"}
        assert res[1] == 500

def test_csrf_middleware_missing_token(client):
    res = client.post('/api/verify-user') # post without csrf
    assert res.status_code == 400
    assert res.get_json() == {'error': 'CSRF token missing or invalid'}

def test_csrf_middleware_valid_token(app, client, mocker):
    mocker.patch('app.validate_csrf_token', return_value=True)
    with app.app_context():
        app.ldap_service.search_user.return_value = None
    res = client.post('/api/verify-user', json={"username": "test"})
    assert res.status_code == 404 # passed CSRF, hits auth logic

def test_csrf_cookie_set(client):
    res = client.get('/health')
    cookies = res.headers.getlist('Set-Cookie')
    assert any('csrf_token=' in c for c in cookies)
