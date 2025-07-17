import logging
from flask import request

audit_logger = logging.getLogger('audit')

def setup_audit_log(app):
    # 配置审计日志记录器
    handler = logging.FileHandler('logs/audit.log')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    audit_logger.addHandler(handler)
    audit_logger.setLevel(logging.INFO)

def audit_log(action, user, details):
    """记录审计日志"""
    ip_address = request.remote_addr
    audit_logger.info(f'Action: {action}, User: {user}, IP: {ip_address}, Details: {details}')