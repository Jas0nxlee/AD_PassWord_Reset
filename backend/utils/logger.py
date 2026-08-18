import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def _formatter():
    return logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')


def _secure_file(path):
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def setup_logger(app):
    log_dir = Path(app.config['LOG_DIR'])
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / 'app.log'

    formatter = _formatter()
    file_handler = RotatingFileHandler(log_path, maxBytes=1024 * 1024, backupCount=10)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    _secure_file(log_path)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    for existing_handler in root_logger.handlers:
        existing_handler.close()
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)

    app.logger.handlers.clear()
    app.logger.propagate = True
    app.logger.setLevel(logging.INFO)
    app.logger.info('Application startup')
