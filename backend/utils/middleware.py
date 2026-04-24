import logging
from flask import request, jsonify

SENSITIVE_HEADERS = {'authorization', 'cookie', 'set-cookie'}
SENSITIVE_FIELDS = {'password', 'new_password', 'token', 'code', 'email'}

# 配置日志
logging.basicConfig(level=logging.INFO)


def _redact_value(key, value):
    if key.lower() in SENSITIVE_FIELDS:
        return '[REDACTED]'
    return value


def _sanitize_mapping(mapping):
    sanitized = {}
    for key, value in mapping.items():
        if key.lower() in SENSITIVE_HEADERS:
            sanitized[key] = '[REDACTED]'
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_mapping(value)
        elif isinstance(value, list):
            sanitized[key] = [
                _sanitize_mapping(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = _redact_value(key, value)
    return sanitized


def _sanitize_body():
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        return _sanitize_mapping(payload)
    if payload is not None:
        return '[NON-DICT PAYLOAD]'
    return '[NO JSON BODY]'


def _sanitize_response_body(response):
    try:
        payload = response.get_json(silent=True)
    except Exception:
        payload = None

    if isinstance(payload, dict):
        return _sanitize_mapping(payload)
    return '[NON-JSON RESPONSE]'

def register_middleware(app):
    @app.before_request
    def log_request_info():
        """在每次请求前记录请求信息"""
        app.logger.info('Request: %s %s', request.method, request.path)
        app.logger.info('Headers: %s', _sanitize_mapping(dict(request.headers)))
        app.logger.info('Body: %s', _sanitize_body())

    @app.after_request
    def log_response_info(response):
        """在每次请求后记录响应信息"""
        app.logger.info('Response: %s', response.status)
        # 避免在直接传递模式下调用get_data()
        try:
            if hasattr(response, 'direct_passthrough') and response.direct_passthrough:
                app.logger.info('Response data: [Direct passthrough mode - data not accessible]')
            else:
                app.logger.info('Response data: %s', _sanitize_response_body(response))
        except Exception as e:
            app.logger.info('Response data: [Unable to access - %s]', str(e))
        return response

    @app.errorhandler(Exception)
    def handle_exception(e):
        """处理未捕获的异常"""
        app.logger.error(f"Unhandled Exception: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500
