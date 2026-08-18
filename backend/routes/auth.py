import logging

from flask import Blueprint, current_app, jsonify, request

from utils.audit import audit_log
from utils.security import password_meets_policy

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

GENERIC_CODE_RESPONSE = {
    'message': 'If the account is eligible, a verification code will be sent.'
}


def _username_from(data):
    username = data.get('username') if isinstance(data, dict) else None
    if not isinstance(username, str):
        return None
    username = username.strip()
    if not username or len(username) > 128 or any(ord(character) < 32 for character in username):
        return None
    return username


def _deliver_verification_code(email_service, verification_service, username, email, subject, body, reservation):
    if email_service.send_email(email, subject, body):
        verification_service.activate_code(username, reservation)
    else:
        verification_service.discard_code(username, reservation)
        logger.error('Unable to deliver verification code')


@auth_bp.route('/csrf', methods=['GET'])
def csrf_token():
    return '', 204


@auth_bp.route('/verify-user', methods=['POST'])
def verify_user():
    data = request.get_json()
    if not _username_from(data):
        return jsonify({'error': 'Username is required'}), 400
    return jsonify(GENERIC_CODE_RESPONSE), 200


@auth_bp.route('/send-code', methods=['POST'])
def send_code():
    data = request.get_json()
    username = _username_from(data)
    if not username:
        return jsonify({'error': 'Username is required'}), 400

    user = current_app.ldap_service.search_user(username)
    if not user or not user.email:
        return jsonify(GENERIC_CODE_RESPONSE), 200

    code_result = current_app.verification_service.begin_code(username)
    if not code_result['success']:
        return jsonify(GENERIC_CODE_RESPONSE), 200

    subject = 'Your Password Reset Code'
    body = (
        f"Your verification code is: {code_result['code']}\n\n"
        'This code expires in 5 minutes. If you did not request it, ignore this email.'
    )
    queued = current_app.email_dispatcher.submit(
        _deliver_verification_code,
        current_app.email_service,
        current_app.verification_service,
        username,
        user.email,
        subject,
        body,
        code_result['reservation'],
    )
    if not queued:
        current_app.verification_service.discard_code(username, code_result['reservation'])
    return jsonify(GENERIC_CODE_RESPONSE), 200


@auth_bp.route('/verify-code', methods=['POST'])
def verify_code():
    data = request.get_json()
    username = _username_from(data)
    code = data.get('code') if isinstance(data, dict) else None
    if not username or not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        return jsonify({'error': 'Username and a 6-digit code are required'}), 400

    result = current_app.verification_service.verify_code(username, code)
    if not result['success']:
        return jsonify({'error': result['message']}), 400

    token = current_app.reset_token_service.issue(username)
    return jsonify({'message': 'Code verified successfully', 'token': token}), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    username = _username_from(data)
    new_password = data.get('new_password') if isinstance(data, dict) else None
    token = data.get('token') if isinstance(data, dict) else None
    if not username or not isinstance(new_password, str) or not isinstance(token, str):
        return jsonify({'error': 'Username, new password and token are required'}), 400

    if not password_meets_policy(
        new_password,
        username,
        current_app.config['PASSWORD_MIN_LENGTH'],
        current_app.config['PASSWORD_MAX_LENGTH'],
    ):
        return jsonify({'error': 'Password does not meet policy requirements'}), 400

    if not current_app.reset_token_service.consume(token, username):
        audit_log('PASSWORD_RESET_REJECTED', username, {'reason': 'invalid_or_used_token'})
        return jsonify({'error': 'Invalid or expired token'}), 401

    user = current_app.ldap_service.search_user(username)
    if not user:
        audit_log('PASSWORD_RESET_FAILURE', username, {'reason': 'user_not_found'})
        return jsonify({'error': 'Unable to reset password'}), 400

    if not current_app.ldap_service.reset_password(user.distinguished_name, new_password):
        audit_log('PASSWORD_RESET_FAILURE', username, {'user_dn': user.distinguished_name})
        return jsonify({'error': 'Failed to reset password'}), 500

    audit_log('PASSWORD_RESET_SUCCESS', username, {'user_dn': user.distinguished_name})
    if user.email:
        current_app.email_dispatcher.submit(
            current_app.email_service.send_email,
            user.email,
            'Your password was reset',
            'Your Active Directory password was reset. Contact support immediately if this was not you.',
        )
    return jsonify({'message': 'Password reset successfully'}), 200
