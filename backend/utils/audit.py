import logging
from flask import request

audit_logger = logging.getLogger('audit')


def _mask_dn(value):
    if not value:
        return ''
    parts = [part for part in str(value).split(',') if part]
    masked_parts = []
    for part in parts:
        if '=' not in part:
            masked_parts.append(part)
            continue
        key, raw = part.split('=', 1)
        key_upper = key.upper()
        if key_upper in {'CN', 'OU'}:
            masked = raw[0] + '***' if raw else '***'
            masked_parts.append(f'{key}={masked}')
        elif key_upper == 'DC':
            masked_parts.append(f'{key}=***')
        else:
            masked_parts.append(f'{key}=***')
    return ','.join(masked_parts)


def _sanitize_details(details):
    sanitized = dict(details or {})
    if 'user_dn' in sanitized:
        sanitized['user_dn'] = _mask_dn(sanitized['user_dn'])
    return sanitized

def setup_audit_log(app):
    # 配置审计日志记录器
    if any(isinstance(handler, logging.FileHandler) and getattr(handler, 'baseFilename', '').endswith('logs/audit.log')
           for handler in audit_logger.handlers):
        return
    handler = logging.FileHandler('logs/audit.log')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    audit_logger.addHandler(handler)
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False

def audit_log(action, user, details):
    """记录审计日志"""
    ip_address = request.remote_addr
    audit_logger.info(f'Action: {action}, User: {user}, IP: {ip_address}, Details: {_sanitize_details(details)}')
