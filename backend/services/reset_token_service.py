import hashlib
import secrets
import threading
import time

from services.verification_service import normalize_username


class ResetTokenService:
    """线程安全的单进程一次性重置令牌存储。"""

    def __init__(self, ttl=600):
        self.ttl = ttl
        self._records = {}
        self._lock = threading.RLock()

    @staticmethod
    def _digest(token):
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    def issue(self, username):
        identifier = normalize_username(username)
        token = secrets.token_urlsafe(32)
        now = time.monotonic()
        with self._lock:
            self._cleanup_locked(now)
            self._records = {
                digest: record
                for digest, record in self._records.items()
                if record['username'] != identifier
            }
            self._records[self._digest(token)] = {
                'username': identifier,
                'expires_at': now + self.ttl,
            }
        return token

    def consume(self, token, username):
        if not isinstance(token, str) or not token:
            return False
        identifier = normalize_username(username)
        digest = self._digest(token)
        now = time.monotonic()
        with self._lock:
            self._cleanup_locked(now)
            record = self._records.pop(digest, None)
            return bool(record and record['username'] == identifier)

    def _cleanup_locked(self, now):
        self._records = {
            digest: record
            for digest, record in self._records.items()
            if record['expires_at'] > now
        }
