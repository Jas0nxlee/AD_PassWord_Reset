import logging
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _mask_email(email):
    if not email or '@' not in email:
        return ''
    local, domain = email.split('@', 1)
    return f'{local[:1]}***@{domain}'


class EmailService:
    def __init__(self, config):
        self.smtp_server = config['SMTP_SERVER']
        self.smtp_port = config['SMTP_PORT']
        self.smtp_username = config['SMTP_USERNAME']
        self.smtp_password = config['SMTP_PASSWORD']
        self.use_ssl = config['SMTP_USE_SSL']
        self.ca_cert_path = config.get('SMTP_CA_CERT_PATH')
        self.timeout = config['SMTP_TIMEOUT']
        self.logger = logging.getLogger(__name__)

    def _tls_context(self):
        return ssl.create_default_context(cafile=self.ca_cert_path)

    def send_email(self, to_address, subject, body):
        message = MIMEMultipart()
        message['From'] = self.smtp_username
        message['To'] = to_address
        message['Subject'] = Header(subject, 'utf-8')
        message.attach(MIMEText(body, 'plain', 'utf-8'))

        try:
            context = self._tls_context()
            if self.use_ssl:
                with smtplib.SMTP_SSL(
                    self.smtp_server,
                    self.smtp_port,
                    timeout=self.timeout,
                    context=context,
                ) as server:
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(message)
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=self.timeout) as server:
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(message)
            self.logger.info('Email sent successfully to %s', _mask_email(to_address))
            return True
        except (OSError, smtplib.SMTPException, ssl.SSLError) as exc:
            self.logger.error('Email delivery failed (%s)', type(exc).__name__)
            return False
