from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

# 导入蓝图
from routes.auth import auth_bp
# from routes.user import user_bp

# 导入中间件
from utils.middleware import register_middleware
from utils.security import generate_csrf_token, validate_csrf_token
from utils.logger import setup_logger
from utils.audit import setup_audit_log

# 导入配置
from config import Config
from services.ldap_service import LDAPService
import logging

def create_app():
    import os
    # Set OPENSSL_CONF environment variable before Flask app initialization
    # This ensures OpenSSL 3.x loads the legacy provider for MD4 support
    # os.environ['OPENSSL_CONF'] = 'd:\\Users\\jingping.li\\Desktop\\ad-reset\\legacy-openssl.cnf'
    """创建并配置Flask应用"""
    app = Flask(__name__)

    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Initialize LDAPService
    app.ldap_service = LDAPService()

    # 从配置对象加载配置
    app.config.from_object(Config)

    # 配置CORS，允许所有来源的跨域请求
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # 初始化速率限制器
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=Config.RATELIMIT_STORAGE_URI
    )

    # 注册中间件
    register_middleware(app)

    # @app.before_request
    # def csrf_protect():
    #     if request.method == "POST":
    #         if not validate_csrf_token():
    #             return jsonify({'error': 'CSRF token missing or invalid'}), 400

    @app.after_request
    def set_csrf_cookie(response):
        if response:
            response.set_cookie('csrf_token', generate_csrf_token())
        return response

    # 对认证蓝图应用速率限制
    limiter.limit("10 per minute")(auth_bp)

    # 注册蓝图
    app.register_blueprint(auth_bp, url_prefix='/api')

    # 设置日志
    setup_logger(app)
    setup_audit_log(app)
    # app.register_blueprint(user_bp, url_prefix='/api/user')

    # 基本的健康检查路由
    @app.route('/health')
    def health_check():
        return jsonify({"status": "ok"}), 200

    # 静态文件路由
    @app.route('/')
    def serve_frontend():
        frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')
        return send_file(os.path.join(frontend_path, 'index.html'))

    @app.route('/<path:path>')
    def serve_static(path):
        frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')
        file_path = os.path.join(frontend_path, path)
        if os.path.exists(file_path):
            return send_file(file_path)
        # 如果文件不存在，返回index.html用于SPA路由
        return send_file(os.path.join(frontend_path, 'index.html'))

    # 注册错误处理器
    @app.errorhandler(404)
    def not_found_error(error):
        # 对于API路由返回JSON错误，对于其他路由返回前端页面
        if request.path.startswith('/api/'):
            return jsonify({"error": "Not Found"}), 404
        else:
            frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')
            return send_file(os.path.join(frontend_path, 'index.html'))

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal Server Error"}), 500

    return app