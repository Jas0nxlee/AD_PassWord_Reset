import hashlib
import hmac
import logging
import ssl
from dataclasses import dataclass
from urllib.parse import urlparse

from ldap3 import ALL, NTLM, SIMPLE, Connection, Server, Tls
from ldap3.core.exceptions import LDAPBindError, LDAPException, LDAPSocketOpenError
from ldap3.extend.microsoft.modifyPassword import ad_modify_password
from ldap3.utils.conv import escape_filter_chars


@dataclass(frozen=True)
class LDAPUser:
    username: str
    email: str | None
    distinguished_name: str


class LDAPService:
    """每次操作创建独立的安全 LDAP 连接，避免跨线程共享状态。"""

    def __init__(self, config):
        self.server_name = self._normalize_server(config['LDAP_SERVER'])
        self.port = config['LDAP_PORT']
        self.base_dn = config['LDAP_BASE_DN']
        self.user = config['LDAP_USER']
        self.password = config['LDAP_PASSWORD']
        self.domain = config['LDAP_DOMAIN']
        self.auth_mode = config['LDAP_AUTH_MODE']
        self.compatibility_mode = config.get('LDAP_COMPATIBILITY_MODE', False)
        self.certificate_fingerprint = config.get('LDAP_CERT_SHA256', '').lower()
        self.ca_cert_path = config.get('LDAP_CA_CERT_PATH')
        self.connect_timeout = config['LDAP_CONNECT_TIMEOUT']
        self.receive_timeout = config['LDAP_RECEIVE_TIMEOUT']
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def _normalize_server(value):
        if '://' not in value:
            return value
        parsed = urlparse(value)
        if parsed.scheme.lower() != 'ldaps' or not parsed.hostname:
            raise ValueError('LDAP_SERVER must be a hostname or an ldaps:// URL')
        return parsed.hostname

    @staticmethod
    def _mask_dn(value):
        if not value:
            return ''
        masked_parts = []
        for part in str(value).split(','):
            if '=' not in part:
                masked_parts.append('***')
                continue
            key, raw = part.split('=', 1)
            masked_parts.append(f'{key}={raw[:1]}***' if raw else f'{key}=***')
        return ','.join(masked_parts)

    def _bind_user(self):
        if self.auth_mode == 'SIMPLE':
            return self.user
        if '\\' in self.user:
            return self.user
        username = self.user.split('@', 1)[0]
        domain = self.domain.split('.', 1)[0].upper()
        return f'{domain}\\{username}'

    def _create_connection(self):
        if self.compatibility_mode:
            tls = Tls(
                validate=ssl.CERT_NONE,
                version=ssl.PROTOCOL_TLSv1_2,
                ciphers='DEFAULT:@SECLEVEL=0',
            )
        else:
            tls = Tls(
                validate=ssl.CERT_REQUIRED,
                version=ssl.PROTOCOL_TLS_CLIENT,
                ca_certs_file=self.ca_cert_path,
            )
        server = Server(
            self.server_name,
            port=self.port,
            use_ssl=True,
            get_info=ALL,
            tls=tls,
            connect_timeout=self.connect_timeout,
        )
        authentication = NTLM if self.auth_mode == 'NTLM' else SIMPLE
        connection = Connection(
            server,
            user=self._bind_user(),
            password=self.password,
            authentication=authentication,
            auto_bind=False,
            auto_referrals=False,
            receive_timeout=self.receive_timeout,
            raise_exceptions=True,
        )
        connection.open()
        if connection.closed:
            raise LDAPSocketOpenError('Unable to open LDAPS connection')

        if self.compatibility_mode:
            certificate = connection.socket.getpeercert(binary_form=True)
            actual_fingerprint = hashlib.sha256(certificate or b'').hexdigest()
            if not certificate or not hmac.compare_digest(actual_fingerprint, self.certificate_fingerprint):
                connection.close()
                raise LDAPSocketOpenError('LDAP certificate fingerprint mismatch')

        if not connection.bind():
            connection.close()
            raise LDAPBindError('LDAP bind failed')
        return connection

    def search_user(self, username):
        safe_username = escape_filter_chars(username)
        search_filter = f'(&(objectClass=user)(sAMAccountName={safe_username}))'
        connection = None
        try:
            connection = self._create_connection()
            found = connection.search(
                self.base_dn,
                search_filter,
                attributes=['distinguishedName', 'mail', 'sAMAccountName'],
                size_limit=1,
            )
            if not found or not connection.entries:
                return None
            entry = connection.entries[0]
            return LDAPUser(
                username=str(entry.sAMAccountName.value),
                email=entry.mail.value if hasattr(entry, 'mail') else None,
                distinguished_name=str(entry.distinguishedName.value),
            )
        except LDAPException as exc:
            self.logger.error('LDAP user lookup failed (%s)', type(exc).__name__)
            return None
        finally:
            if connection is not None and connection.bound:
                connection.unbind()

    def reset_password(self, user_dn, new_password):
        connection = None
        masked_dn = self._mask_dn(user_dn)
        try:
            connection = self._create_connection()
            success = ad_modify_password(connection, user_dn, new_password, None)
            result_code = connection.result.get('result') if connection.result else None
            if success and result_code == 0:
                self.logger.info('Password reset completed for %s', masked_dn)
                return True
            self.logger.error('Password reset rejected for %s (result=%s)', masked_dn, result_code)
            return False
        except LDAPException as exc:
            self.logger.error('LDAP password reset failed for %s (%s)', masked_dn, type(exc).__name__)
            return False
        finally:
            if connection is not None and connection.bound:
                connection.unbind()
