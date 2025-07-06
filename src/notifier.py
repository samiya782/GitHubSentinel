import smtplib
import markdown2
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from logger import LOG
import ssl

class Notifier:
    def __init__(self, email_settings, report_type='GitHubSentinel'):
        self.email_settings = email_settings
        self.report_type = report_type
    
    def notify(self, repo, report):
        if self.email_settings:
            self.send_email(repo, report)
        else:
            LOG.warning("邮件设置未配置正确，无法发送通知")

    def send_email(self, repo, report):
        LOG.info(f"准备向 {self.email_settings['to']} 发送邮件")

        # (处理收件人列表的代码，建议保留)
        if isinstance(self.email_settings['to'], str):
            to_addrs = [addr.strip() for addr in self.email_settings['to'].split(',')]
        else:
            to_addrs = self.email_settings['to']

        msg = MIMEMultipart()
        msg['From'] = self.email_settings['from']
        msg['To'] = ", ".join(to_addrs)
        msg['Subject'] = f"[{self.report_type}] {repo} 进展简报"

        html_report = markdown2.markdown(report, extras=["tables", "fenced-code-blocks"])
        msg.attach(MIMEText(html_report, 'html', 'utf-8'))

        server = None  # 1. 初始化 server 为 None
        try:
            context = ssl.create_default_context()
            # 2. 手动创建和连接 server
            server = smtplib.SMTP_SSL(
                self.email_settings['smtp_server'],
                self.email_settings['smtp_port'],
                context=context
            )

            LOG.debug("登录SMTP服务器...")
            server.login(self.email_settings['from'], self.email_settings['password'])

            LOG.debug("发送邮件...")
            server.sendmail(self.email_settings['from'], to_addrs, msg.as_string())

            LOG.info("邮件发送成功！")  # 邮件发送成功后记录日志

        except Exception as e:
            # 3. 这个 except 块现在只处理连接、登录、发送过程中的错误
            LOG.error(f"发送邮件过程中失败：{str(e)}")

        finally:
            # 4. finally 块确保无论成功还是失败，都会尝试关闭连接
            if server:
                try:
                    LOG.debug("正在关闭SMTP连接...")
                    server.quit()
                    LOG.debug("SMTP连接已优雅关闭。")
                except Exception as e_quit:
                    # 5. 捕获并记录关闭连接时的错误，但将其视为警告，因为它不影响邮件发送
                    LOG.warning(f"关闭SMTP连接时发生错误（邮件可能已发送成功）: {str(e_quit)}")

if __name__ == '__main__':
    from config import Config
    config = Config()
    notifier = Notifier(config.email)

    test_repo = "DjangoPeng/openai-quickstart"
    test_report = """
# DjangoPeng/openai-quickstart 项目进展

## 时间周期：2024-08-24

## 新增功能
- Assistants API 代码与文档

## 主要改进
- 适配 LangChain 新版本

## 修复问题
- 关闭了一些未解决的问题。

"""
    notifier.notify(test_repo, test_report)
