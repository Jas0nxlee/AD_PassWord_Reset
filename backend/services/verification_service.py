import random
import string
import time

class VerificationService:
    def __init__(self):
        self.codes = {}
        self.code_length = 6
        self.expire_time = 300  # 验证码有效期为5分钟
        self.cooldown_time = 60  # 验证码发送冷却时间（秒）
        self.max_attempts = 5

    def generate_code(self, identifier):
        """为指定标识符生成验证码"""
        # 清理过期验证码，防止内存泄漏
        self._cleanup_expired()

        existing_record = self.codes.get(identifier)
        if existing_record and time.time() - existing_record['sent_at'] < self.cooldown_time:
            return {
                'success': False,
                'reason': 'cooldown',
                'message': 'Verification code was sent recently. Please wait before requesting another code.'
            }

        code = ''.join(random.choices(string.digits, k=self.code_length))
        self.codes[identifier] = {
            'code': code,
            'timestamp': time.time(),
            'sent_at': time.time(),
            'failed_attempts': 0
        }
        return {
            'success': True,
            'reason': 'sent',
            'message': 'Verification code generated successfully.',
            'code': code
        }

    def _cleanup_expired(self):
        """清理所有已过期的验证码"""
        current_time = time.time()
        expired_keys = [k for k, v in self.codes.items() 
                        if current_time - v['timestamp'] > self.expire_time]
        for key in expired_keys:
            del self.codes[key]

    def verify_code(self, identifier, code):
        """验证指定标识符的验证码"""
        if identifier not in self.codes:
            return {
                'success': False,
                'reason': 'missing',
                'message': 'Invalid or expired code.'
            }

        stored_code_info = self.codes[identifier]
        if time.time() - stored_code_info['timestamp'] > self.expire_time:
            # 验证码已过期
            del self.codes[identifier]
            return {
                'success': False,
                'reason': 'expired',
                'message': 'Invalid or expired code.'
            }

        if stored_code_info['code'] == code:
            # 验证成功后删除验证码
            del self.codes[identifier]
            return {
                'success': True,
                'reason': 'verified',
                'message': 'Code verified successfully.'
            }

        stored_code_info['failed_attempts'] += 1
        if stored_code_info['failed_attempts'] >= self.max_attempts:
            del self.codes[identifier]
            return {
                'success': False,
                'reason': 'max_attempts_exceeded',
                'message': 'Verification code has expired. Please request a new code.'
            }

        return {
            'success': False,
            'reason': 'invalid',
            'message': 'Invalid or expired code.'
        }

# 实例化服务
verification_service = VerificationService()
