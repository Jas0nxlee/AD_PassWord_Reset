import os
import sys
from dotenv import load_dotenv

# 处理PyInstaller打包后的路径
if getattr(sys, 'frozen', False):
    # 如果是打包后的exe文件
    application_path = os.path.dirname(sys.executable)
else:
    # 如果是开发环境
    application_path = os.path.dirname(os.path.dirname(__file__))

# 指定.env文件的完整路径
env_path = os.path.join(application_path, '.env')

# 加载.env文件中的环境变量
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"Loaded .env from: {env_path}")
else:
    print(f"Warning: .env file not found at: {env_path}")
    # 尝试从当前目录加载
    load_dotenv()
    print("Attempting to load .env from current directory")

class Config:
    """应用配置类，从环境变量加载配置"""

    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a-default-secret-key')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
    FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')

    # LDAP配置
    LDAP_SERVER = os.environ.get('LDAP_SERVER')
    LDAP_PORT = int(os.environ.get('LDAP_PORT', 636))
    LDAP_USE_SSL = os.environ.get('LDAP_USE_SSL', 'True').lower() in ('true', '1', 't')
    LDAP_BASE_DN = os.environ.get('LDAP_BASE_DN')
    LDAP_USER = os.environ.get('LDAP_USER')
    LDAP_PASSWORD = os.environ.get('LDAP_PASSWORD')
    LDAP_DOMAIN = os.environ.get('LDAP_DOMAIN')
    LDAP_VERIFY_CERT = os.environ.get('LDAP_VERIFY_CERT', 'False').lower() in ('true', '1', 't')

    # SMTP邮件配置
    SMTP_SERVER = os.environ.get('SMTP_SERVER')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')

    # 服务器配置
    SERVER_IP = os.environ.get('SERVER_IP')

    # 速率限制配置
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')

    @staticmethod
    def validate():
        """验证必要的环境变量是否已设置"""
        required_vars = [
            'LDAP_SERVER', 'LDAP_BASE_DN', 'LDAP_USER', 'LDAP_PASSWORD',
            'SMTP_SERVER', 'SMTP_USERNAME', 'SMTP_PASSWORD', 'SERVER_IP'
        ]
        missing_vars = [var for var in required_vars if not getattr(Config, var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# 在模块加载时执行验证
try:
    Config.validate()
except ValueError as e:
    print(f"Configuration Error: {e}")
    # 在实际应用中，你可能希望在这里退出程序
    # import sys
    # sys.exit(1)