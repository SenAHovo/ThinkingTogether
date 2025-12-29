"""
邮件发送服务模块
使用腾讯云(QQ邮箱) SMTP服务发送验证码邮件
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import Optional


class EmailService:
    """邮件服务类"""

    def __init__(self):
        """从环境变量加载配置"""
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.qq.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "465"))
        self.sender_email = os.getenv("SENDER_EMAIL")
        self.sender_auth_code = os.getenv("SENDER_AUTH_CODE")

        # 不在初始化时抛出错误，而是在发送邮件时检查
        if not all([self.sender_email, self.sender_auth_code]):
            print("[WARNING] 邮件配置不完整，邮件功能将不可用。请检查.env文件中的SMTP配置")
            self.configured = False
        else:
            self.configured = True

    def _create_email_template(self, purpose: str, code: str) -> tuple[str, str]:
        """
        根据用途创建邮件模板

        Args:
            purpose: 邮件用途 (register, reset_password, change_password)
            code: 验证码

        Returns:
            (subject, html_content)
        """
        templates = {
            "register": (
                "【智炬五维】注册验证码",
                f"""
                <html>
                  <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0;">
                      <h1 style="color: white; margin: 0; font-size: 24px;">欢迎加入智炬五维协同学习平台</h1>
                    </div>
                    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                      <p style="color: #333; font-size: 16px;">您好！</p>
                      <p style="color: #666; font-size: 15px;">感谢您注册<strong>智炬五维协同学习平台</strong>。您的注册验证码是：</p>
                      <div style="background: white; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                        <h2 style="color: #667eea; font-size: 32px; margin: 0; letter-spacing: 5px;">{code}</h2>
                      </div>
                      <p style="color: #999; font-size: 14px;">该验证码<strong>10分钟内</strong>有效，请勿泄露给他人。</p>
                      <p style="color: #999; font-size: 14px;">如果您没有注册账户，请忽略此邮件。</p>
                    </div>
                    <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                      <p>此邮件由系统自动发送，请勿回复</p>
                    </div>
                  </body>
                </html>
                """
            ),
            "reset_password": (
                "【智炬五维】密码重置验证码",
                f"""
                <html>
                  <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 30px; border-radius: 10px 10px 0 0;">
                      <h1 style="color: white; margin: 0; font-size: 24px;">密码重置请求</h1>
                    </div>
                    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                      <p style="color: #333; font-size: 16px;">您好！</p>
                      <p style="color: #666; font-size: 15px;">我们收到了您的<strong>密码重置请求</strong>。您的验证码是：</p>
                      <div style="background: white; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                        <h2 style="color: #f5576c; font-size: 32px; margin: 0; letter-spacing: 5px;">{code}</h2>
                      </div>
                      <p style="color: #999; font-size: 14px;">该验证码<strong>10分钟内</strong>有效，请勿泄露给他人。</p>
                      <p style="color: #999; font-size: 14px;">如果您没有请求重置密码，请忽略此邮件或联系管理员。</p>
                    </div>
                    <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                      <p>此邮件由系统自动发送，请勿回复</p>
                    </div>
                  </body>
                </html>
                """
            ),
            "change_password": (
                "【智炬五维】修改密码验证码",
                f"""
                <html>
                  <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 30px; border-radius: 10px 10px 0 0;">
                      <h1 style="color: white; margin: 0; font-size: 24px;">修改密码验证</h1>
                    </div>
                    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                      <p style="color: #333; font-size: 16px;">您好！</p>
                      <p style="color: #666; font-size: 15px;">您正在<strong>修改账户密码</strong>，您的验证码是：</p>
                      <div style="background: white; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                        <h2 style="color: #4facfe; font-size: 32px; margin: 0; letter-spacing: 5px;">{code}</h2>
                      </div>
                      <p style="color: #999; font-size: 14px;">该验证码<strong>10分钟内</strong>有效，请勿泄露给他人。</p>
                      <p style="color: #999; font-size: 14px;">如果您没有请求修改密码，请立即联系管理员。</p>
                    </div>
                    <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                      <p>此邮件由系统自动发送，请勿回复</p>
                    </div>
                  </body>
                </html>
                """
            ),
            "bind_email": (
                "【智炬五维】绑定邮箱验证码",
                f"""
                <html>
                  <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); padding: 30px; border-radius: 10px 10px 0 0;">
                      <h1 style="color: white; margin: 0; font-size: 24px;">绑定邮箱验证</h1>
                    </div>
                    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                      <p style="color: #333; font-size: 16px;">您好！</p>
                      <p style="color: #666; font-size: 15px;">您正在<strong>绑定邮箱</strong>，您的验证码是：</p>
                      <div style="background: white; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                        <h2 style="color: #43e97b; font-size: 32px; margin: 0; letter-spacing: 5px;">{code}</h2>
                      </div>
                      <p style="color: #999; font-size: 14px;">该验证码<strong>10分钟内</strong>有效，请勿泄露给他人。</p>
                      <p style="color: #999; font-size: 14px;">如果您没有请求绑定邮箱，请忽略此邮件。</p>
                    </div>
                    <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                      <p>此邮件由系统自动发送，请勿回复</p>
                    </div>
                  </body>
                </html>
                """
            )
        }

        return templates.get(purpose, templates["register"])

    def send_verification_code(self, recipient_email: str, code: str, purpose: str = "register") -> bool:
        """
        发送验证码邮件

        Args:
            recipient_email: 收件人邮箱
            code: 验证码
            purpose: 邮件用途 (register, reset_password, change_password, bind_email)

        Returns:
            bool: 发送是否成功
        """
        # 检查配置
        if not self.configured:
            print(f"[ERROR] 邮件服务未配置，无法发送验证码到 {recipient_email}")
            return False

        server = None
        try:
            # 获取邮件模板
            subject, html_content = self._create_email_template(purpose, code)

            # 构建邮件对象
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = Header(subject, 'utf-8').encode()

            # 附加HTML内容
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            # 建立SSL安全连接
            server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            server.login(self.sender_email, self.sender_auth_code)

            # 发送邮件 - 这是关键步骤
            server.sendmail(self.sender_email, [recipient_email], msg.as_string())

            # 如果sendmail没有抛出异常，说明邮件发送成功
            print(f"[SUCCESS] 验证码邮件已成功发送至 {recipient_email} (用途: {purpose})")
            return True

        except smtplib.SMTPAuthenticationError:
            print(f"[ERROR] 邮件认证失败，请检查SMTP配置")
            return False
        except smtplib.SMTPException as e:
            print(f"[ERROR] SMTP错误: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] 发送邮件时发生错误: {type(e).__name__}: {e}")
            return False
        finally:
            # 确保连接被正确关闭
            if server is not None:
                try:
                    server.quit()
                except:
                    # 忽略关闭连接时的异常，因为邮件已经发送成功了
                    pass


# 创建全局实例
email_service = EmailService()
