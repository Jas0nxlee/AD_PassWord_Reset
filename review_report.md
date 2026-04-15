# AD Password Reset Architecture and Security Review

## Architecture Review
1. **In-Memory State**: `VerificationService` stores codes in an in-memory dictionary. This breaks when the application is scaled to multiple workers or restarted. A centralized store like Redis should be used.
2. **Global App State**: The app is stateful (in-memory rate limiter `memory://`). Same issue as above for multi-worker deployments.
3. **Legacy Dependencies**: The application uses legacy OpenSSL configurations (MD4 support via `legacy-openssl.cnf`) for NTLM.

## Security Review
1. **Account Takeover via Parameter Tampering (`backend/routes/auth.py`)**:
   In `/send-code`, the application checks if the username exists in LDAP, but it sends the verification code to the `email` address provided in the *request body*, not the email retrieved from LDAP. An attacker can request a password reset for an admin user but provide their own email address to receive the code.
2. **LDAP Injection (`backend/services/ldap_service.py`)**:
   In `search_user`, the filter is constructed via unsafe string concatenation: `f"(&(objectClass=user)(sAMAccountName={username}))"`. If a user inputs `admin)(|(objectClass=*)`, the filter becomes `(&(objectClass=user)(sAMAccountName=admin)(|(objectClass=*)))`, bypassing intended restrictions.
3. **Missing CSRF Protection (`backend/app.py`)**:
   The `@app.before_request def csrf_protect():` logic is commented out, making state-changing endpoints vulnerable to Cross-Site Request Forgery (CSRF).
