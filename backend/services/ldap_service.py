import os
import ssl
import subprocess
import sys
from ldap3 import Server, Connection, ALL, MODIFY_REPLACE, NTLM, SIMPLE
from ldap3.core.exceptions import LDAPException
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import Config

# Set OpenSSL configuration to enable legacy algorithms (MD4) for NTLM authentication
os.environ['OPENSSL_CONF'] = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'legacy-openssl.cnf')

# Try to enable legacy providers for OpenSSL
try:
    import ssl
    # Force reload of ssl module with new OpenSSL config
    if hasattr(ssl, '_create_unverified_context'):
        ssl._create_default_https_context = ssl._create_unverified_context
except Exception as e:
    print(f"Warning: Could not configure SSL for legacy support: {e}")

class LDAPService:
    def __init__(self):
        self.server_uri = Config.LDAP_SERVER
        self.port = Config.LDAP_PORT
        self.use_ssl = Config.LDAP_USE_SSL
        self.base_dn = Config.LDAP_BASE_DN
        self.user = Config.LDAP_USER
        self.password = Config.LDAP_PASSWORD
        self.domain = Config.LDAP_DOMAIN
        self.conn = None

    def _get_ntlm_user(self):
        if '@' in self.user:
            username_part = self.user.split('@')[0]
            if self.domain:
                domain_part = self.domain.split('.')[0].upper()
                return f"{domain_part}\\{username_part}"
        return self.user

    def connect(self):
        """Establish connection to LDAP server, trying SSL first then non-SSL."""
        ntlm_user = self._get_ntlm_user()

        conn = None

        # First try SSL connection if configured
        if self.use_ssl:
            try:
                print(f"Attempting SSL connection on port {self.port}...")
                print(f"Using NTLM user: {ntlm_user}")

                # Try with more permissive SSL settings
                from ldap3 import Tls
                tls_configuration = Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLS, ciphers='ALL:@SECLEVEL=0')
                server = Server(self.server_uri, port=self.port, use_ssl=True, get_info=ALL, tls=tls_configuration)
                conn = Connection(server, user=ntlm_user, password=self.password, authentication=NTLM, auto_bind=True)
                if conn.bound:
                    self.conn = conn
                    print("SSL connection successful")
                    return True
            except Exception as ssl_error:
                print(f"SSL connection failed: {ssl_error}")
                print("Trying non-SSL connection on port 389...")

        # If SSL failed or not configured, try non-SSL connection with NTLM
        if conn is None or not conn.bound:
            try:
                print(f"Using NTLM user: {ntlm_user}")
                server = Server(self.server_uri, port=389, use_ssl=False, get_info=ALL)
                conn = Connection(server, user=ntlm_user, password=self.password, authentication=NTLM, auto_bind=True)
                if conn.bound:
                    self.conn = conn
                    print("Non-SSL connection successful")
                    return True
            except Exception as non_ssl_error:
                print(f"NTLM authentication failed: {non_ssl_error}")
                print("Trying simple authentication...")
                
                # Try simple authentication as fallback
                try:
                    # Use the original user format for simple auth
                    simple_user = self.user if '@' in self.user else f"{self.user}@{self.domain}"
                    conn = Connection(server, user=simple_user, password=self.password, authentication=SIMPLE, auto_bind=True)
                    if conn.bound:
                        self.conn = conn
                        print("Simple authentication successful")
                        return True
                except Exception as simple_error:
                    print(f"Simple authentication also failed: {simple_error}")
                    raise LDAPException(f"All authentication methods failed. NTLM: {non_ssl_error}, Simple: {simple_error}")

        raise LDAPException("Failed to connect to LDAP server.")

    def search_user(self, username):
        """Search for a user by sAMAccountName."""
        if not self.conn and not self.connect():
            return None
        
        search_filter = f"(&(objectClass=user)(sAMAccountName={username}))"
        try:
            self.conn.search(self.base_dn, search_filter, attributes=['distinguishedName', 'mail', 'sAMAccountName', 'cn'])
            if self.conn.entries:
                return self.conn.entries[0]
            return None
        except LDAPException as e:
            print(f"LDAP search failed: {e}")
            return None

    def reset_password(self, user_dn, new_password):
        """Resets the password for a user in Active Directory.

        This method tries to use SSL connection for security, but will attempt
        password reset even on non-SSL connections if SSL is not available.
        """
        import logging
        from ldap3.extend.microsoft.modifyPassword import ad_modify_password

        logger = logging.getLogger(__name__)

        if not self.conn and not self.connect():
            logger.error("Failed to establish LDAP connection for password reset.")
            return False

        # Check if we have SSL connection
        has_ssl = self.conn.server.ssl
        if has_ssl:
            logger.info(f"Using secure SSL connection for password reset of user: {user_dn}")
        else:
            logger.warning(f"Using non-SSL connection for password reset of user: {user_dn}. This is less secure but may be necessary in some environments.")

        logger.info(f"Attempting password reset for user: {user_dn}")

        # Method 1: Use the ad_modify_password extended operation (preferred method for SSL)
        if has_ssl:
            try:
                # The ad_modify_password function returns True on success, but we also check the result code.
                success = ad_modify_password(self.conn, user_dn, new_password, None)
                
                # A successful operation returns a result code of 0.
                if success and self.conn.result and self.conn.result.get('result') == 0:
                    logger.info(f"SUCCESS: Password for user '{user_dn}' was reset successfully using ad_modify_password.")
                    return True
                else:
                    logger.error(f"ad_modify_password failed for user '{user_dn}'. Result: {self.conn.result}")

            except LDAPException as e:
                logger.error(f"LDAP error during ad_modify_password for user '{user_dn}': {e}")
            except Exception as ext_error:
                logger.error(f"An unexpected error occurred with ad_modify_password for user '{user_dn}': {ext_error}")

        # Method 2: Try unicodePwd (works with SSL)
        if has_ssl:
            logger.warning(f"Trying unicodePwd method for user '{user_dn}' over SSL.")
            try:
                unicode_pass = f'"{new_password}"'.encode('utf-16le')
                self.conn.modify(user_dn, {'unicodePwd': [(MODIFY_REPLACE, [unicode_pass])]})
                
                if self.conn.result and self.conn.result.get('result') == 0:
                    logger.info(f"SUCCESS: Password for user '{user_dn}' was reset successfully using unicodePwd.")
                    return True
                else:
                    logger.error(f"unicodePwd method failed for user '{user_dn}'. Result: {self.conn.result}")

            except LDAPException as e:
                logger.error(f"LDAP error during unicodePwd modification for user '{user_dn}': {e}")

        # Method 3: Try userPassword (works without SSL in some environments)
        logger.warning(f"Trying userPassword method for user '{user_dn}'.")
        try:
            self.conn.modify(user_dn, {'userPassword': [(MODIFY_REPLACE, [new_password.encode('utf-8')])]})
            
            if self.conn.result and self.conn.result.get('result') == 0:
                logger.info(f"SUCCESS: Password for user '{user_dn}' was reset successfully using userPassword.")
                return True
            else:
                logger.error(f"userPassword method failed for user '{user_dn}'. Result: {self.conn.result}")

        except LDAPException as e:
            logger.error(f"LDAP error during userPassword modification for user '{user_dn}': {e}")

        # Method 4: Try pwdLastSet reset + unicodePwd (alternative approach)
        if has_ssl:
            logger.warning(f"Trying pwdLastSet reset + unicodePwd for user '{user_dn}'.")
            try:
                # First reset pwdLastSet to 0, then to -1, then set password
                self.conn.modify(user_dn, {'pwdLastSet': [(MODIFY_REPLACE, [0])]})
                unicode_pass = f'"{new_password}"'.encode('utf-16le')
                self.conn.modify(user_dn, {'unicodePwd': [(MODIFY_REPLACE, [unicode_pass])]})
                self.conn.modify(user_dn, {'pwdLastSet': [(MODIFY_REPLACE, [-1])]})
                
                if self.conn.result and self.conn.result.get('result') == 0:
                    logger.info(f"SUCCESS: Password for user '{user_dn}' was reset successfully using pwdLastSet method.")
                    return True
                else:
                    logger.error(f"pwdLastSet method failed for user '{user_dn}'. Result: {self.conn.result}")

            except LDAPException as e:
                logger.error(f"LDAP error during pwdLastSet method for user '{user_dn}': {e}")

        logger.error(f"CRITICAL: All password reset methods failed for user '{user_dn}'.")
        return False

    def disconnect(self):
        """Disconnect from the LDAP server."""
        if self.conn and self.conn.bound:
            self.conn.unbind()
            print("LDAP connection closed.")