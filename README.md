# AD Password Reset Application

English | [中文](README_zh.md)

A web-based Active Directory user password reset application with email verification, audit logging, and a hardened password reset workflow.

## Features

- 🔐 Active Directory password reset workflow
- 📧 Email verification code delivery and validation
- 🛡️ Audit logging for password reset success/failure
- 🚀 React + TypeScript frontend
- 🔒 Request logging with sensitive-field redaction
- ⏱️ Verification code cooldown and retry limit protection

## Technology Stack

- **Backend**: Python + Flask
- **Frontend**: React + TypeScript + Vite
- **Directory Service**: LDAP / Active Directory
- **Email Service**: SMTP
- **Testing**: pytest
- **Logging**: Python logging + rotating file logs

## Requirements

- Python 3.8+
- Node.js 22 LTS recommended
- Active Directory environment
- SMTP email service

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AD_PassWord_Reset
   ```

2. **Install backend dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   Create `.env` in the project root and provide at least:
   ```env
   LDAP_SERVER=...
   LDAP_PORT=636
   LDAP_BASE_DN=...
   LDAP_DOMAIN=...
   LDAP_USER=...
   LDAP_PASSWORD=...
   SMTP_SERVER=...
   SMTP_PORT=465
   SMTP_USERNAME=...
   SMTP_PASSWORD=...
   SERVER_IP=127.0.0.1
   SECRET_KEY=replace-with-a-strong-random-value
   FLASK_ENV=production
   FLASK_DEBUG=False
   RATELIMIT_STORAGE_URI=memory://
   ```

4. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

5. **Run the application**
   ```bash
   python run.py
   ```

   The app starts at [http://localhost:5001](http://localhost:5001).

## Recommended Node Setup

This project has been verified with **Node.js 22 LTS**.

If you installed Node locally under `~/.local/node`, make sure your shell loads it first:

```bash
export PATH="$HOME/.local/node/node-v22.22.2-darwin-arm64/bin:$PATH"
```

## Frontend Commands

```bash
cd frontend
npm install
npm run dev
npm run build
```

## Desktop Build and GitHub Release

This repository includes a GitHub Actions workflow at `.github/workflows/release.yml` that:

- builds the frontend with Node.js 22
- installs backend dependencies and `PyInstaller`
- packages the app for **Windows** and **macOS**
- uploads zipped artifacts to the workflow run
- automatically creates or updates a GitHub Release when you push a tag like `v1.0.0`

### Trigger a release

```bash
git tag v1.0.0
git push origin v1.0.0
```

### Notes

- Windows release contains `AD_Password_Reset.exe`; double-clicking it starts the local Flask/Waitress service in a console window and opens the browser automatically.
- macOS release contains `AD_Password_Reset.app`; double-clicking it starts the same local service and opens the browser automatically.
- Both packages serve the built frontend from `frontend/dist`.
- Runtime configuration still depends on your `.env` and target AD/SMTP environment.
- The macOS `.app` is not signed or notarized in this workflow.

## Backend Tests

Run the regression tests added for the password reset hardening changes:

```bash
$HOME/Library/Python/3.9/bin/pytest -q tests/test_auth_security.py
```

Covered scenarios include:

- masked email response for `/api/verify-user`
- `/api/send-code` username-only behavior
- verification code cooldown enforcement
- verification code invalidation after repeated failures
- config validation failure when required environment variables are missing

## Logging

Application logs are written to:

- `logs/app.log`
- `logs/audit.log`

Current logging behavior:

- request/response logs redact sensitive fields such as password, token, code, email, and cookies
- SMTP delivery logs redact recipient email addresses
- audit logs preserve success/failure records while redacting distinguished names (DN)

To clear current logs before a fresh verification run:

```bash
: > logs/app.log
: > logs/audit.log
```

## Security Notes

- Do not commit `.env` files or real credentials.
- Use LDAPS / secure SMTP in production.
- Review audit logs regularly.
- The current verification code store is in-memory; restarting the process clears pending codes.
- Existing historical logs are not automatically rewritten when redaction rules change.

## Project Structure

```text
AD_PassWord_Reset/
├── backend/                # Flask backend
│   ├── app.py
│   ├── config.py
│   ├── routes/
│   ├── services/
│   └── utils/
├── frontend/               # React + TypeScript frontend
├── logs/                   # Runtime logs
├── tests/                  # pytest regression tests
├── requirements.txt
└── run.py
```
