import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ================= 配置区域 / Configuration =================
# 请在此处直接修改您的邮箱配置信息
SMTP_CONFIG = {
    "SMTP_HOST": "smtp.qq.com",        # 邮件服务器地址，例如 smtp.qq.com
    "SMTP_PORT": 587,                  # 端口，通常为 465 (SSL) 或 587 (STARTTLS)
    "SMTP_USER": "3298807098@qq.com", # 发件人邮箱账号
    "SMTP_PASS": "okkphacewdkidbad",      # 邮箱授权码或密码
    "SMTP_SSL": False,                 # 是否使用 SSL (如果端口是 465 通常为 True)
    "SMTP_STARTTLS": True,             # 是否使用 STARTTLS (如果端口是 587 通常为 True)
    "SMTP_FROM": "3298807098@qq.com", # 发件人显示地址 (通常与 user 相同)
    "SMTP_TIMEOUT": 20                 # 连接超时时间(秒)
}
# ===========================================================

def send_email(to_email: str, subject: str, html_body: str):
    # 从配置字典中读取
    host = SMTP_CONFIG["SMTP_HOST"]
    port = int(SMTP_CONFIG["SMTP_PORT"])
    user = SMTP_CONFIG["SMTP_USER"]
    password = SMTP_CONFIG["SMTP_PASS"]
    use_ssl = SMTP_CONFIG["SMTP_SSL"]
    use_starttls = SMTP_CONFIG["SMTP_STARTTLS"]
    from_addr = SMTP_CONFIG["SMTP_FROM"] or user
    timeout = int(SMTP_CONFIG["SMTP_TIMEOUT"])

    if not host or not port or not to_email:
        return False, "缺少SMTP配置或收件人"
    
    # 简单的检查，防止用户忘记修改配置
    if "your_email" in user or "your_password" in password:
        return False, "请先在 getnewcspapers/delivery/emailer.py 文件中填写正确的邮箱配置信息"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    part = MIMEText(html_body or "", "html", "utf-8")
    msg.attach(part)
    try:
        if use_ssl or port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=timeout)
        else:
            server = smtplib.SMTP(host, port, timeout=timeout)
            if use_starttls:
                server.starttls()
        if user and password:
            server.login(user, password)
        server.sendmail(from_addr, [to_email], msg.as_string())
        server.quit()
        return True, "发送成功"
    except Exception as e:
        try:
            server.quit()
        except Exception:
            pass
        return False, f"发送失败: {str(e)}"

