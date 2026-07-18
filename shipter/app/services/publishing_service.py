import logging
import smtplib
from email.mime.text import MIMEText
import requests

logger = logging.getLogger(__name__)

TELEGRAM_API_TIMEOUT = 10
SMTP_TIMEOUT = 15


def test_telegram_connection(bot_token: str) -> tuple[bool, str]:
    """Проверяет валидность Telegram bot token через getMe."""
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getMe",
            timeout=TELEGRAM_API_TIMEOUT
        )
        data = resp.json()
        if resp.status_code == 200 and data.get('ok'):
            return True, data['result'].get('username', '')
        return False, data.get('description', 'Неверный токен бота')
    except requests.RequestException as e:
        logger.error(f"Telegram connection test error: {e}")
        return False, 'Не удалось подключиться к Telegram API'


def publish_telegram(integration, text: str) -> tuple[bool, str]:
    """Публикует текст в Telegram-канал через бот. Возвращает (успех, сообщение об ошибке)."""
    config = integration.get_config()
    bot_token = config.get('bot_token')
    chat_id = config.get('chat_id')

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=TELEGRAM_API_TIMEOUT
        )
        data = resp.json()
        if resp.status_code == 200 and data.get('ok'):
            return True, ''
        return False, data.get('description', 'Ошибка отправки в Telegram')
    except requests.RequestException as e:
        logger.error(f"Telegram publish error: {e}")
        return False, 'Не удалось отправить сообщение в Telegram'


def send_email_smtp(integration, subject: str, body: str, recipients: list[str]) -> tuple[bool, str]:
    """Отправляет письмо через SMTP-креды пользователя (не через общий аккаунт платформы)."""
    config = integration.get_config()
    host = config.get('smtp_host')
    port = int(config.get('smtp_port', 587))
    username = config.get('smtp_username')
    password = config.get('smtp_password')
    use_tls = config.get('use_tls', True)

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = username
    msg['To'] = ', '.join(recipients)

    try:
        with smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT) as server:
            if use_tls:
                server.starttls()
            server.login(username, password)
            server.sendmail(username, recipients, msg.as_string())
        return True, ''
    except smtplib.SMTPException as e:
        logger.error(f"SMTP publish error: {e}")
        return False, 'Не удалось отправить письмо через указанный SMTP'
    except OSError as e:
        logger.error(f"SMTP connection error: {e}")
        return False, 'Не удалось подключиться к SMTP-серверу'
