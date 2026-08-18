import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import request

audit_logger = logging.getLogger('audit')


def _mask_dn(value):
    if not value:
        return ''
    parts = []
    for part in str(value).split(','):
        if '=' not in part:
            parts.append('***')
            continue
        key, raw = part.split('=', 1)
        parts.append(f'{key}={raw[:1]}***' if raw else f'{key}=***')
    return ','.join(parts)


def _sanitize_details(details):
    sanitized = dict(details or {})
    if 'user_dn' in sanitized:
        sanitized['user_dn'] = _mask_dn(sanitized['user_dn'])
    return sanitized


def setup_audit_log(app):
    log_dir = Path(app.config['LOG_DIR'])
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / 'audit.log'

    for existing_handler in audit_logger.handlers:
        existing_handler.close()
    audit_logger.handlers.clear()
    handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=20)
    handler.setFormatter(logging.Formatter('%(message)s'))
    audit_logger.addHandler(handler)
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False
    try:
        os.chmod(log_path, 0o600)
    except OSError:
        pass


def audit_log(action, user, details):
    event = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'action': action,
        'user': str(user).replace('\r', '').replace('\n', ''),
        'ip': request.remote_addr,
        'details': _sanitize_details(details),
    }
    audit_logger.info(json.dumps(event, ensure_ascii=False, separators=(',', ':')))
