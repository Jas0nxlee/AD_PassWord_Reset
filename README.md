# AD Password Reset Application

English | [中文](README_zh.md)

A Flask and React self-service password reset application for Active Directory. Verification codes and one-time reset transactions are stored in the application process; Redis is not required.

## Security properties

- Certificate-verified LDAPS only, with no plaintext LDAP fallback
- One LDAP connection per operation instead of shared mutable connections
- Cryptographically secure verification codes and one-time reset tokens
- Locked in-memory state for cooldowns, attempt limits, expiry, and token consumption
- Uniform reset-request responses for existing and non-existing users
- Server-side password policy, CSRF validation, request-size limits, and security headers
- Request bodies, headers, passwords, codes, and tokens are excluded from application logs

## Requirements

- Python 3.12
- Node.js 22 LTS
- Active Directory reachable through LDAPS
- SMTP with a trusted TLS certificate

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
# Fill in the real settings and generate a strong SECRET_KEY.

cd frontend
npm ci
npm run build
cd ..

python run.py
```

The desktop configuration listens only on [http://127.0.0.1:5002](http://127.0.0.1:5002).

## Required configuration changes

- `SECRET_KEY` must contain at least 32 characters.
- `LDAP_USE_SSL=true` and `LDAP_VERIFY_CERT=true` are mandatory.
- Configure `LDAP_CA_CERT_PATH` when the internal CA is not in the system trust store.
- SMTP certificate validation cannot be disabled.
- An old `.env` containing `LDAP_VERIFY_CERT=false` will be rejected at startup.

For a legacy SHA-1 certificate that cannot be replaced immediately, set `LDAP_COMPATIBILITY_MODE=true` and pin the exact leaf certificate through `LDAP_CERT_SHA256`. The fingerprint is checked before LDAP bind credentials are sent. This is a temporary migration mode; replace the certificate and return to strict validation when possible.

See [.env.example](.env.example) for the complete configuration.

## Single-process limitation

Verification state, reset tokens, and rate limits are process-local:

- Run one Waitress process; multiple threads are supported.
- Pending transactions are invalidated by an application restart.
- Horizontal scaling requires replacing the in-memory stores with a shared atomic store first.

## Verification

```bash
pytest -q

cd frontend
npm run lint
npm run build
npm audit --omit=dev
cd ..

pip-audit -r requirements.txt
```

## Production deployment

- Keep `SERVER_HOST=127.0.0.1` for desktop use.
- For a server deployment, use an HTTPS reverse proxy and set `COOKIE_SECURE=true`.
- Grant the LDAP service account password-reset rights only for the intended OU.
- Rotate the LDAP credential, SMTP credential, and `SECRET_KEY` regularly.
- Protect and monitor `logs/app.log` and `logs/audit.log`.

## Releases

`.github/workflows/release.yml` runs tests, lint, builds, and dependency audits before packaging Windows and macOS artifacts. Tags matching `v*` publish a GitHub Release.

The macOS bundle is not currently signed or notarized.

For packaged runs, place `.env` in the Windows application directory or next to the macOS `.app` bundle.
