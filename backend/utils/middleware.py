from flask import jsonify, request
from werkzeug.exceptions import HTTPException


def register_middleware(app):
    @app.before_request
    def log_request_info():
        app.logger.info('Request: %s %s', request.method, request.path)

    @app.after_request
    def log_response_info(response):
        app.logger.info('Response: %s %s', response.status_code, request.path)
        return response

    @app.errorhandler(Exception)
    def handle_exception(error):
        if isinstance(error, HTTPException):
            return jsonify({'error': error.description}), error.code
        app.logger.error('Unhandled exception (%s)', type(error).__name__, exc_info=True)
        return jsonify({'error': 'An unexpected error occurred. Please try again later.'}), 500
