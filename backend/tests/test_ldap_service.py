import pytest
from unittest.mock import patch, MagicMock
from ldap3.core.exceptions import LDAPException
import os
import sys

# Ensure backend is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.ldap_service import LDAPService

@pytest.fixture
def ldap_service():
    with patch('services.ldap_service.Config') as MockConfig:
        MockConfig.LDAP_SERVER = "ldap://test.server"
        MockConfig.LDAP_PORT = 636
        MockConfig.LDAP_USE_SSL = True
        MockConfig.LDAP_BASE_DN = "dc=test,dc=com"
        MockConfig.LDAP_USER = "testuser"
        MockConfig.LDAP_PASSWORD = "testpassword"
        MockConfig.LDAP_DOMAIN = "TEST"
        return LDAPService()

def test_get_ntlm_user(ldap_service):
    assert ldap_service._get_ntlm_user() == "testuser"

    ldap_service.user = "admin@test.com"
    ldap_service.domain = "TEST.COM"
    assert ldap_service._get_ntlm_user() == "TEST\\admin"

    ldap_service.user = "admin@test.com"
    ldap_service.domain = None
    assert ldap_service._get_ntlm_user() == "admin@test.com"

@patch('services.ldap_service.Connection')
@patch('services.ldap_service.Server')
def test_connect_ssl_success(MockServer, MockConnection, ldap_service):
    mock_conn = MagicMock()
    mock_conn.bound = True
    MockConnection.return_value = mock_conn

    assert ldap_service.connect() is True
    assert ldap_service.conn == mock_conn

@patch('services.ldap_service.Connection')
@patch('services.ldap_service.Server')
def test_connect_ssl_fail_non_ssl_success(MockServer, MockConnection, ldap_service):
    mock_conn_fail = MagicMock()
    mock_conn_fail.bound = False

    mock_conn_success = MagicMock()
    mock_conn_success.bound = True

    # First call throws exception to simulate SSL failure, second succeeds
    MockConnection.side_effect = [Exception("SSL Failed"), mock_conn_success]

    assert ldap_service.connect() is True
    assert ldap_service.conn == mock_conn_success

@patch('services.ldap_service.Connection')
@patch('services.ldap_service.Server')
def test_connect_all_fail(MockServer, MockConnection, ldap_service):
    MockConnection.side_effect = Exception("Failed")
    with pytest.raises(LDAPException):
        ldap_service.connect()

@patch('services.ldap_service.Connection')
@patch('services.ldap_service.Server')
def test_connect_non_ssl_success_without_ssl_config(MockServer, MockConnection, ldap_service):
    ldap_service.use_ssl = False

    mock_conn_success = MagicMock()
    mock_conn_success.bound = True

    MockConnection.return_value = mock_conn_success
    assert ldap_service.connect() is True

@patch('services.ldap_service.Connection')
@patch('services.ldap_service.Server')
def test_connect_simple_auth_success(MockServer, MockConnection, ldap_service):
    ldap_service.use_ssl = False

    mock_conn_fail = MagicMock()
    mock_conn_fail.bound = False

    mock_conn_success = MagicMock()
    mock_conn_success.bound = True

    # NTLM fails, simple auth succeeds
    MockConnection.side_effect = [Exception("NTLM Failed"), mock_conn_success]

    assert ldap_service.connect() is True

def test_search_user_connect_fail(ldap_service):
    with patch.object(ldap_service, 'connect', return_value=False):
        assert ldap_service.search_user("test") is None

def test_search_user_success(ldap_service):
    mock_conn = MagicMock()
    mock_conn.entries = ["UserEntry"]
    ldap_service.conn = mock_conn

    assert ldap_service.search_user("test*user") == "UserEntry"
    mock_conn.search.assert_called_with(
        ldap_service.base_dn,
        "(&(objectClass=user)(sAMAccountName=test\\2auser))",
        attributes=['distinguishedName', 'mail', 'sAMAccountName', 'cn']
    )

def test_search_user_not_found(ldap_service):
    mock_conn = MagicMock()
    mock_conn.entries = []
    ldap_service.conn = mock_conn

    assert ldap_service.search_user("test") is None

def test_search_user_ldap_exception(ldap_service):
    mock_conn = MagicMock()
    mock_conn.search.side_effect = LDAPException("Search failed")
    ldap_service.conn = mock_conn

    assert ldap_service.search_user("test") is None

def test_reset_password_connect_fail(ldap_service):
    with patch.object(ldap_service, 'connect', return_value=False):
        assert ldap_service.reset_password("dn", "pass") is False

@patch('ldap3.extend.microsoft.modifyPassword.ad_modify_password')
def test_reset_password_method1_success(mock_ad_modify, ldap_service):
    mock_conn = MagicMock()
    mock_conn.server.ssl = True
    mock_conn.result = {'result': 0}
    ldap_service.conn = mock_conn

    mock_ad_modify.return_value = True

    assert ldap_service.reset_password("dn", "pass") is True

@patch('ldap3.extend.microsoft.modifyPassword.ad_modify_password')
def test_reset_password_method1_fail_method2_success(mock_ad_modify, ldap_service):
    mock_conn = MagicMock()
    mock_conn.server.ssl = True

    def modify_side_effect(*args, **kwargs):
        if 'unicodePwd' in args[1]:
            mock_conn.result = {'result': 0}
        return True

    mock_conn.modify.side_effect = modify_side_effect
    ldap_service.conn = mock_conn

    mock_ad_modify.return_value = False

    assert ldap_service.reset_password("dn", "pass") is True

@patch('ldap3.extend.microsoft.modifyPassword.ad_modify_password')
def test_reset_password_method2_fail_method3_success(mock_ad_modify, ldap_service):
    mock_conn = MagicMock()
    mock_conn.server.ssl = True

    def modify_side_effect(*args, **kwargs):
        if 'userPassword' in args[1]:
            mock_conn.result = {'result': 0}
        else:
            mock_conn.result = {'result': 53} # Unwilling to perform
        return True

    mock_conn.modify.side_effect = modify_side_effect
    ldap_service.conn = mock_conn

    mock_ad_modify.side_effect = LDAPException("Method 1 failed")

    assert ldap_service.reset_password("dn", "pass") is True

@patch('ldap3.extend.microsoft.modifyPassword.ad_modify_password')
def test_reset_password_method3_fail_method4_success(mock_ad_modify, ldap_service):
    mock_conn = MagicMock()
    mock_conn.server.ssl = True

    def modify_side_effect(*args, **kwargs):
        if 'pwdLastSet' in args[1]:
            mock_conn.result = {'result': 0}
        else:
            mock_conn.result = {'result': 53}
        return True

    mock_conn.modify.side_effect = modify_side_effect
    ldap_service.conn = mock_conn

    mock_ad_modify.side_effect = Exception("Method 1 ext error")

    assert ldap_service.reset_password("dn", "pass") is True

def test_reset_password_all_fail(ldap_service):
    mock_conn = MagicMock()
    mock_conn.server.ssl = False
    mock_conn.result = {'result': 53}
    mock_conn.modify.side_effect = LDAPException("Failed modify")
    ldap_service.conn = mock_conn

    assert ldap_service.reset_password("dn", "pass") is False

def test_disconnect(ldap_service):
    mock_conn = MagicMock()
    mock_conn.bound = True
    ldap_service.conn = mock_conn

    ldap_service.disconnect()
    mock_conn.unbind.assert_called_once()

def test_disconnect_no_conn(ldap_service):
    ldap_service.disconnect() # Shouldn't raise

def test_reset_password_method2_ldap_exception(ldap_service):
    mock_conn = MagicMock()
    mock_conn.server.ssl = True

    def modify_side_effect(*args, **kwargs):
        if 'userPassword' in args[1]:
            mock_conn.result = {'result': 0}
            return True
        raise LDAPException("unicodePwd/pwdLastSet failed")

    mock_conn.modify.side_effect = modify_side_effect
    ldap_service.conn = mock_conn

    with patch('ldap3.extend.microsoft.modifyPassword.ad_modify_password', return_value=False):
        assert ldap_service.reset_password("dn", "pass") is True # Continues to method 3 and succeeds

def test_reset_password_method4_ldap_exception(ldap_service):
    mock_conn = MagicMock()
    mock_conn.server.ssl = True

    def modify_side_effect(*args, **kwargs):
        if 'pwdLastSet' in args[1]:
            raise LDAPException("pwdLastSet failed")
        elif 'userPassword' in args[1]:
            mock_conn.result = {'result': 53}
        return True

    mock_conn.modify.side_effect = modify_side_effect
    ldap_service.conn = mock_conn

    with patch('ldap3.extend.microsoft.modifyPassword.ad_modify_password', return_value=False):
        assert ldap_service.reset_password("dn", "pass") is False # All fail

def test_connect_ntlm_fail_simple_auth_fail(ldap_service):
    with patch('services.ldap_service.Connection') as MockConnection:
        with patch('services.ldap_service.Server'):
            ldap_service.use_ssl = False
            MockConnection.side_effect = Exception("NTLM Failed")
            # Wait, MockConnection is called twice. If side_effect is a single exception it throws on first call.
            # To test the simple_error, we need it to fail on the second call too.
            # Actually, `raise LDAPException(f"All authentication methods failed. NTLM: {non_ssl_error}, Simple: {simple_error}")`

            MockConnection.side_effect = [Exception("NTLM fail"), Exception("Simple auth fail")]
            with pytest.raises(LDAPException) as excinfo:
                ldap_service.connect()
            assert "All authentication methods failed" in str(excinfo.value)

def test_connect_all_fail_reach_end(ldap_service):
    with patch('services.ldap_service.Connection') as MockConnection:
        with patch('services.ldap_service.Server'):
            ldap_service.use_ssl = False

            # Make the first connection return unbound to skip exception flow
            mock_conn_fail = MagicMock()
            mock_conn_fail.bound = False
            MockConnection.return_value = mock_conn_fail

            with pytest.raises(LDAPException) as exc:
                ldap_service.connect()
            assert "Failed to connect" in str(exc.value)

def test_reset_password_pwdlastset_fail(ldap_service):
    mock_conn = MagicMock()
    mock_conn.server.ssl = True

    def modify_side_effect(*args, **kwargs):
        if 'pwdLastSet' in args[1]:
            mock_conn.result = {'result': 53}
            return True
        elif 'userPassword' in args[1]:
            mock_conn.result = {'result': 53}
            return True
        elif 'unicodePwd' in args[1]:
            mock_conn.result = {'result': 53}
            return True
        return True

    mock_conn.modify.side_effect = modify_side_effect
    ldap_service.conn = mock_conn

    with patch('ldap3.extend.microsoft.modifyPassword.ad_modify_password', return_value=False):
        assert ldap_service.reset_password("dn", "pass") is False
def test_ssl_except():
    import sys
    import importlib

    from services import ldap_service
    import builtins

    original_hasattr = builtins.hasattr
    def custom_hasattr(obj, name):
        if name == '_create_unverified_context':
            raise Exception("Mocked ssl warning")
        return original_hasattr(obj, name)

    builtins.hasattr = custom_hasattr
    try:
        importlib.reload(ldap_service)
    finally:
        builtins.hasattr = original_hasattr
