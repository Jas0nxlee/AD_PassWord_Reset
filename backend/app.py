import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import safe_join

from config import Config
from routes.auth import auth_bp
from services.email_dispatcher import EmailDispatcher
from services.email_service import EmailService
from services.ldap_service import LDAPService
from services.reset_token_service import ResetTokenService
from services.verification_service import VerificationService
from utils.audit import setup_audit_log
from utils.logger import setup_logger
from utils.middleware import register_middleware
from utils.security import generate_csrf_token, validate_csrf_token


def create_app():
    Config.validate()
    app = Flask(__name__)
    app.config.from_object(Config)

    app.ldap_service = LDAPService(app.config)
    app.email_service = EmailService(app.config)
    app.email_dispatcher = EmailDispatcher(
        workers=app.config['EMAIL_WORKERS'],
        queue_limit=app.config['EMAIL_QUEUE_LIMIT'],
        asynchronous=app.config['EMAIL_ASYNC'],
    )
    app.verification_service = VerificationService(
        expire_time=app.config['VERIFICATION_CODE_TTL'],
        cooldown_time=app.config['VERIFICATION_CODE_COOLDOWN'],
        max_attempts=app.config['VERIFICATION_MAX_ATTEMPTS'],
    )
    app.reset_token_service = ResetTokenService(ttl=app.config['RESET_TOKEN_TTL'])

    setup_logger(app)
    setup_audit_log(app)
    if app.config['LDAP_COMPATIBILITY_MODE']:
        app.logger.warning('LDAP legacy certificate compatibility mode is enabled with SHA-256 pinning')
    register_middleware(app)

    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=['200 per day', '50 per hour'],
        storage_uri=app.config['RATELIMIT_STORAGE_URI'],
        headers_enabled=True,
    )
    limiter.limit('10 per minute')(auth_bp)

    @app.before_request
    def csrf_protect():
        if request.method == 'POST' and not validate_csrf_token():
            return jsonify({'error': 'CSRF token missing or invalid'}), 400

    @app.after_request
    def apply_security_headers(response):
        response.set_cookie(
            'csrf_token',
            generate_csrf_token(),
            secure=app.config['CSRF_COOKIE_SECURE'],
            httponly=False,
            samesite='Strict',
            path='/',
        )
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        if request.path.startswith('/api/') or response.mimetype == 'text/html':
            response.headers['Cache-Control'] = 'no-store'
        return response

    app.register_blueprint(auth_bp, url_prefix='/api')

    if getattr(sys, 'frozen', False):
        project_root = Path(sys._MEIPASS)
    else:
        project_root = Path(__file__).resolve().parent.parent
    frontend_path = project_root / 'frontend' / 'dist'

    @app.route('/health')
    def health_check():
        return jsonify({'status': 'ok'}), 200

    @app.route('/')
    def serve_frontend():
        return send_file(frontend_path / 'index.html')

    @app.route('/<path:path>')
    def serve_static(path):
        resolved = safe_join(str(frontend_path), path)
        if resolved is None:
            return 'Not Found', 404
        resolved_path = Path(resolved)
        if resolved_path.is_file():
            return send_from_directory(frontend_path, path)
        return send_file(frontend_path / 'index.html')

    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Not Found'}), 404
        return 'Not Found', 404

    return app
