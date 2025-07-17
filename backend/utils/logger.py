import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(app):
    # 创建logs目录（如果不存在）
    if not os.path.exists('logs'):
        os.mkdir('logs')

    # 移除旧的处理器，以防重载时重复添加
    for handler in list(app.logger.handlers):
        app.logger.removeHandler(handler)

    # 配置日志记录器
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)

    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Application startup')

    @app.teardown_appcontext
    def teardown_logger(exception=None):
        for handler in list(app.logger.handlers):
            handler.close()
            app.logger.removeHandler(handler)