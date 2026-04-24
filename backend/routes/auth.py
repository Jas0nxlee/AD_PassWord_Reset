from flask import Blueprint, jsonify, request
from utils.security import generate_token, verify_token
from flask import current_app
from services.email_service import email_service
from services.verification_service import verification_service
from utils.audit import audit_log

# 创建一个名为'auth'的蓝图
auth_bp = Blueprint('auth', __name__)

import logging


def _mask_email(email):
    if not email or '@' not in email:
        return ''
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        return f"{local[0]}*@{domain}" if local else ''
    return f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}@{domain}"


def _get_user_email(user_info):
    if user_info and hasattr(user_info, 'mail') and user_info.mail.value:
        return user_info.mail.value
    return None

@auth_bp.route('/verify-user', methods=['POST'])
def verify_user():
    logging.info("Entered verify_user function")
    data = request.get_json()
    if not data or not data.get('username'):
        return jsonify({'error': 'Username is required'}), 400
    username = str(data.get('username')).strip()

    logging.info("Searching for password reset candidate")
    user_info = current_app.ldap_service.search_user(username)
    masked_email = _mask_email(_get_user_email(user_info))
    logging.info("Password reset candidate lookup completed")
    return jsonify({
        'message': 'If the account is eligible, a verification code can be sent.',
        'masked_email': masked_email
    }), 200

@auth_bp.route('/send-code', methods=['POST'])
def send_code():
    data = request.get_json()
    if not data or not data.get('username'):
        return jsonify({'error': 'Username is required'}), 400
    username = str(data.get('username')).strip()

    # 1. 验证用户是否存在于LDAP中
    user = current_app.ldap_service.search_user(username)
    email = _get_user_email(user)
    if not user or not email:
        return jsonify({"error": "Unable to send verification email."}), 400

    # 2. 生成验证码
    code_result = verification_service.generate_code(username)
    if not code_result['success']:
        status_code = 429 if code_result['reason'] == 'cooldown' else 400
        return jsonify({"error": code_result['message']}), status_code
    code = code_result['code']

    # 3. 发送邮件
    subject = "Your Password Reset Code"
    body = f"Your verification code is: {code}"
    if not email_service.send_email(email, subject, body):
        return jsonify({"error": "Failed to send verification email"}), 500

    return jsonify({"message": "Verification code sent successfully"})


@auth_bp.route('/verify-code', methods=['POST'])
def verify_code():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('code'):
        return jsonify({'error': 'Username and code are required'}), 400
    username = data.get('username')
    code = data.get('code')

    verification_result = verification_service.verify_code(username, code)
    if verification_result['success']:
        token = generate_token({'username': username})
        return jsonify({"message": "Code verified successfully", "token": token})
    if verification_result['reason'] == 'max_attempts_exceeded':
        return jsonify({"error": verification_result['message']}), 400
    return jsonify({"error": verification_result['message']}), 400


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    logging.info("Entered reset_password function")
    data = request.get_json()
    if not data or not data.get('username') or not data.get('new_password') or not data.get('token'):
        return jsonify({'error': 'Username, new password and token are required'}), 400
    username = data.get('username')
    new_password = data.get('new_password')
    token = data.get('token')

    # 1. 验证令牌
    token_data = verify_token(token)
    if not token_data or token_data.get('username') != username:
        return jsonify({'error': 'Invalid or expired token'}), 401

    # 2. 获取用户的DN
    user_info = current_app.ldap_service.search_user(username)
    if not user_info:
        return jsonify({"error": "User not found"}), 404
    user_dn = user_info.distinguishedName.value

    # 3. 重置密码
    if current_app.ldap_service.reset_password(user_dn, new_password):
        audit_log('PASSWORD_RESET_SUCCESS', username, {'user_dn': user_dn})
        return jsonify({"message": "Password reset successfully"})
    else:
        audit_log('PASSWORD_RESET_FAILURE', username, {'user_dn': user_dn, 'error': 'LDAP password reset failed'})
        return jsonify({"error": "Failed to reset password"}), 500
