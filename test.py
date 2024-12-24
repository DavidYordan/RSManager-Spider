import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# SMTP 配置信息
smtp_host = "webhost.dynadot.com"
smtp_port = 587
smtp_username = "admin@swipeshort.com"
smtp_password = "35851746"

# 收件人信息
recipient_email = "xinburuquan@gmail.com"

# 邮件内容
subject = "测试邮件"
body = "这是通过升级后的 Dynadot 企业邮箱发送的测试邮件，使用 Python 脚本实现。"

# 创建 MIME 邮件
message = MIMEMultipart()
message["From"] = smtp_username
message["To"] = recipient_email
message["Subject"] = subject
message.attach(MIMEText(body, "plain"))

try:
    # 开启调试信息
    print("连接到 SMTP 服务器...")
    server = smtplib.SMTP(smtp_host, smtp_port)
    # with smtplib.SMTP(smtp_host, smtp_port) as server:
    print("连接到 SMTP 服务器...")
    server.starttls()  # 使用 STARTTLS 加密
    print("登录 SMTP 服务器...")
    server.login(smtp_username, smtp_password)  # 登录 SMTP 服务器
    print("发送邮件...")
    server.sendmail(smtp_username, recipient_email, message.as_string())  # 发送邮件
    print("邮件发送成功！")
except Exception as e:
    print(f"邮件发送失败：{e}")
