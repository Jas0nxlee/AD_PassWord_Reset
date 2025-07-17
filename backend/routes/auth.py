from flask import Blueprint, jsonify, request
from utils.security import generate_token, verify_token
from flask import current_app
from services.email_service import email_service
from services.verification_service import verification_service
from utils.audit import audit_log

# 创建一个名为'auth'的蓝图
auth_bp = Blueprint('auth', __name__)

import logging

@auth_bp.route('/verify-user', methods=['POST'])
def verify_user():
    logging.info("Entered verify_user function")
    data = request.get_json()
    if not data or not data.get('username'):
        return jsonify({'error': 'Username is required'}), 400
    username = data.get('username')

    logging.info(f"Searching for user: {username}")
    user_info = current_app.ldap_service.search_user(username)
    logging.info(f"LDAP search completed for user: {username}")
    if user_info:
        if hasattr(user_info, 'mail') and user_info.mail.value:
            return jsonify({'message': 'User verified successfully', 'email': user_info.mail.value}), 200
        else:
            return jsonify({'error': 'User found but no email address configured'}), 404
    else:
        return jsonify({'error': 'User not found'}), 404

@auth_bp.route('/send-code', methods=['POST'])
def send_code():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('email'):
        return jsonify({'error': 'Username and email are required'}), 400
    username = data.get('username')
    email = data.get('email')

    # 1. 验证用户是否存在于LDAP中
    user = current_app.ldap_service.search_user(username)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # 2. 生成验证码
    code = verification_service.generate_code(username)

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

    if verification_service.verify_code(username, code):
        token = generate_token({'username': username})
        return jsonify({"message": "Code verified successfully", "token": token})
    else:
        return jsonify({"error": "Invalid or expired code"}), 400


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