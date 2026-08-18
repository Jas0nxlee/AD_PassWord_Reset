import hashlib
import hmac
import secrets
import string
import threading
import time


def normalize_username(username):
    if not isinstance(username, str):
        return ''
    return username.strip().casefold()


class VerificationService:
    """线程安全的单进程验证码存储。"""

    def __init__(self, expire_time=300, cooldown_time=60, max_attempts=5):
        self.codes = {}
        self.code_length = 6
        self.expire_time = expire_time
        self.cooldown_time = cooldown_time
        self.max_attempts = max_attempts
        self._lock = threading.RLock()

    @staticmethod
    def _digest(code):
        return hashlib.sha256(code.encode('utf-8')).hexdigest()

    def begin_code(self, username):
        """原子保留一个待发送验证码，避免并发绕过冷却。"""
        identifier = normalize_username(username)
        if not identifier:
            return {'success': False, 'reason': 'invalid'}

        now = time.monotonic()
        with self._lock:
            self._cleanup_locked(now)
            existing = self.codes.get(identifier)
            if existing and now - existing['sent_at'] < self.cooldown_time:
                return {'success': False, 'reason': 'cooldown'}

            code = ''.join(secrets.choice(string.digits) for _ in range(self.code_length))
            reservation = secrets.token_hex(16)
            self.codes[identifier] = {
                'code_digest': self._digest(code),
                'created_at': now,
                'sent_at': now,
                'failed_attempts': 0,
                'active': False,
                'reservation': reservation,
            }
            return {
                'success': True,
                'reason': 'pending',
                'code': code,
                'reservation': reservation,
            }

    def activate_code(self, username, reservation):
        identifier = normalize_username(username)
        with self._lock:
            record = self.codes.get(identifier)
            if not record or record['reservation'] != reservation:
                return False
            record['active'] = True
            return True

    def discard_code(self, username, reservation):
        identifier = normalize_username(username)
        with self._lock:
            record = self.codes.get(identifier)
            if record and record['reservation'] == reservation:
                del self.codes[identifier]

    def verify_code(self, username, code):
        identifier = normalize_username(username)
        if not identifier or not isinstance(code, str):
            return self._failure('missing', 'Invalid or expired code.')

        now = time.monotonic()
        with self._lock:
            self._cleanup_locked(now)
            record = self.codes.get(identifier)
            if not record or not record['active']:
                return self._failure('missing', 'Invalid or expired code.')

            if hmac.compare_digest(record['code_digest'], self._digest(code)):
                del self.codes[identifier]
                return {'success': True, 'reason': 'verified', 'message': 'Code verified successfully.'}

            record['failed_attempts'] += 1
            if record['failed_attempts'] >= self.max_attempts:
                del self.codes[identifier]
                return self._failure(
                    'max_attempts_exceeded',
                    'Verification code has expired. Please request a new code.',
                )
            return self._failure('invalid', 'Invalid or expired code.')

    def _cleanup_locked(self, now):
        self.codes = {
            identifier: record
            for identifier, record in self.codes.items()
            if now - record['created_at'] <= self.expire_time
        }

    @staticmethod
    def _failure(reason, message):
        return {'success': False, 'reason': reason, 'message': message}
