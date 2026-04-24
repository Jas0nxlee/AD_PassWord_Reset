import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from config import Config


def _mask_email(email):
    if not email or '@' not in email:
        return ''
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        return f"{local[0]}*@{domain}" if local else ''
    return f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}@{domain}"


class EmailService:
    def __init__(self):
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.smtp_username = Config.SMTP_USERNAME
        self.smtp_password = Config.SMTP_PASSWORD
        self.logger = logging.getLogger(__name__)

    def send_email(self, to_address, subject, body):
        """发送邮件"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = to_address
            msg['Subject'] = Header(subject, 'utf-8')

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
                    self.logger.info('Email sent successfully via SSL to %s', _mask_email(to_address))
                    return True
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
                    self.logger.info('Email sent successfully via STARTTLS to %s', _mask_email(to_address))
                    return True
        except Exception as e:
            self.logger.error('Failed to send email: %s', e)
            return False


email_service = EmailService()
