import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header  # 需要导入Header类


def send_email_via_qq():
    """通过QQ邮箱SMTP发送邮件"""
    # 配置参数
    SMTP_SERVER = "smtp.qq.com"
    SMTP_PORT = 465
    SENDER_EMAIL = "1224722493@qq.com"  # 请替换
    SENDER_AUTH_CODE = "rqiglvbtxiebjgfi"  # 请替换
    RECIPIENT_EMAIL = "19139928238@163.com"  # 请替换

    # 1. 定义邮件内容
    subject = "【测试】您的账户验证码"

    # HTML内容
    html_content = """
    <html>
      <body>
        <p>您好！</p>
        <p>您正在进行<strong>账户注册</strong>操作，您的验证码是：</p>
        <h2 style="color: #1890ff;">123456</h2>
        <p>该验证码<strong>10分钟内</strong>有效，请勿泄露给他人。</p>
      </body>
    </html>
    """

    # 2. 构建邮件对象 (关键修正部分)
    msg = MIMEMultipart('alternative')

    # 发件人 - 使用简单格式
    msg['From'] = SENDER_EMAIL

    # 收件人
    msg['To'] = RECIPIENT_EMAIL

    # 主题 - 明确使用UTF-8编码 (修复点)
    msg['Subject'] = Header(subject, 'utf-8').encode()

    # 附加HTML内容 - 明确指定utf-8编码
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    try:
        # 3. 建立SSL安全连接
        print("正在连接到QQ邮件服务器...")
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.set_debuglevel(1)  # 开启调试，可以看到详细过程

        # 4. 登录邮箱
        print("正在登录邮箱...")
        server.login(SENDER_EMAIL, SENDER_AUTH_CODE)

        # 5. 发送邮件
        print("正在发送邮件...")
        server.sendmail(SENDER_EMAIL, [RECIPIENT_EMAIL], msg.as_string())
        print(f"邮件已成功发送至 {RECIPIENT_EMAIL}")

        # 6. 关闭连接
        server.quit()
        return True

    except smtplib.SMTPAuthenticationError:
        print("错误：认证失败！请检查：")
        print(f"  邮箱：{SENDER_EMAIL}")
        print("  是否已开启SMTP服务并获取了正确的授权码")
        return False
    except smtplib.SMTPException as e:
        print(f"SMTP错误：{e}")
        return False
    except Exception as e:
        print(f"未知错误：{type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    success = send_email_via_qq()
    if not success:
        print("发送失败，请检查以上错误信息。")