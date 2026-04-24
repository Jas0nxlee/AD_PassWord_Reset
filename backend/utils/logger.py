import logging
from logging.handlers import RotatingFileHandler
import os


def _build_formatter():
    return logging.Formatter('%(asctime)s %(levelname)s: %(name)s: %(message)s [in %(pathname)s:%(lineno)d]')

def setup_logger(app):
    # 创建logs目录（如果不存在）
    if not os.path.exists('logs'):
        os.mkdir('logs')

    # 避免重复配置
    if getattr(app, '_logger_configured', False):
        return

    formatter = _build_formatter()

    # 统一配置 app logger
    app.logger.handlers.clear()
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False

    # 统一根日志输出到同样的控制台与文件，覆盖 logging.info/getLogger(__name__) 等调用
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    root_file_handler.setFormatter(formatter)
    root_file_handler.setLevel(logging.INFO)

    root_console_handler = logging.StreamHandler()
    root_console_handler.setFormatter(formatter)
    root_console_handler.setLevel(logging.INFO)

    root_logger.addHandler(root_file_handler)
    root_logger.addHandler(root_console_handler)
    root_logger.setLevel(logging.INFO)

    app._logger_configured = True
    app.logger.info('Application startup')
