import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from config import Config

class EmailService:
    def __init__(self):
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.smtp_username = Config.SMTP_USERNAME
        self.smtp_password = Config.SMTP_PASSWORD

    def send_email(self, to_address, subject, body):
        """发送邮件"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = to_address
            msg['Subject'] = Header(subject, 'utf-8')

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # 根据端口选择连接方式
            if self.smtp_port == 465:
                # 使用SSL连接
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
                    print(f"Email sent to {to_address} via SSL")
                    return True
            else:
                # 使用STARTTLS连接
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
                    print(f"Email sent to {to_address} via STARTTLS")
                    return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

# 实例化服务
email_service = EmailService()