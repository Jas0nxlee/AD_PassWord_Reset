# AD Password Reset Application

English | [中文](README_zh.md)

A web-based Active Directory user password reset application with email verification and secure password reset workflow.

## Features

- 🔐 Secure AD password reset
- 📧 Email verification code validation
- 🛡️ Complete audit logging
- 🚀 Modern web interface
- 📱 Responsive design
- 🔒 Multi-layer security protection

## Technology Stack

- **Backend**: Python Flask
- **Frontend**: HTML5, CSS3, JavaScript
- **Directory Service**: LDAP/Active Directory
- **Email Service**: SMTP
- **Logging**: Python logging

## Quick Start

### Requirements

- Python 3.8+
- Active Directory environment
- SMTP email service

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AD_Reset
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   # Copy environment template
   cp .env.example .env
   # Edit .env file with your actual configuration
   ```

5. **Run the application**
   ```bash
   python run.py
   ```

## Environment Configuration

### Required Environment Variables

Copy `.env.example` to `.env` and configure the following variables:

#### LDAP Configuration
- `LDAP_SERVER`: AD server address
- `LDAP_PORT`: LDAP port (usually 636 or 389)
- `LDAP_BASE_DN`: AD base DN
- `LDAP_DOMAIN`: AD domain name
- `LDAP_USER`: Administrator account
- `LDAP_PASSWORD`: Administrator password

#### SMTP Configuration
- `SMTP_SERVER`: Mail server address
- `SMTP_PORT`: SMTP port
- `SMTP_USERNAME`: Sender email
- `SMTP_PASSWORD`: Email password

#### Application Configuration
- `SERVER_IP`: Server IP address
- `SECRET_KEY`: Flask secret key (use strong random value)
- `FLASK_ENV`: Runtime environment (development/production)

## Security Considerations

⚠️ **Important**: 
- Ensure `.env` file is not committed to version control
- Use strong passwords and secure keys in production
- Regularly check audit logs
- Ensure LDAP connections use SSL encryption

## Project Structure

```
AD_Reset/
├── backend/                # Backend code
│   ├── app.py             # Flask application main file
│   ├── config.py          # Configuration management
│   ├── routes/            # Route handlers
│   ├── services/          # Business logic services
│   └── utils/             # Utility functions
├── frontend/              # Frontend code
├── logs/                  # Log files
├── .env.example          # Environment variables template
├── requirements.txt      # Python dependencies
└── run.py               # Application startup file
```

## Contributing

1. Fork the project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter issues or have suggestions, please create an [Issue](../../issues).