import logging
from flask import request, jsonify

# 配置日志
logging.basicConfig(level=logging.INFO)

def register_middleware(app):
    @app.before_request
    def log_request_info():
        """在每次请求前记录请求信息"""
        app.logger.info('Request: %s %s', request.method, request.path)
        app.logger.info('Headers: %s', request.headers)
        app.logger.info('Body: %s', request.get_data())

    @app.after_request
    def log_response_info(response):
        """在每次请求后记录响应信息"""
        app.logger.info('Response: %s', response.status)
        # 避免在直接传递模式下调用get_data()
        try:
            if hasattr(response, 'direct_passthrough') and response.direct_passthrough:
                app.logger.info('Response data: [Direct passthrough mode - data not accessible]')
            else:
                app.logger.info('Response data: %s', response.get_data(as_text=True))
        except Exception as e:
            app.logger.info('Response data: [Unable to access - %s]', str(e))
        return response

    @app.errorhandler(Exception)
    def handle_exception(e):
        """处理未捕获的异常"""
        app.logger.error(f"Unhandled Exception: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500