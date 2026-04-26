import logging
from app.extensions import db, scheduler
from app.models.user import User
from app.models.subscription import Subscription
from datetime import datetime, timezone, timedelta
from flask_mail import Message
from app.extensions import mail
from app.config import Config

logger = logging.getLogger(__name__)

def check_trial_expirations():
    """Проверяет истекающие trial и отправляет напоминания."""
    now = datetime.now(timezone.utc)
    
    # Находим пользователей у которых trial заканчивается через 2 дня
    two_days_later = now + timedelta(days=2)
    
    trial_users = User.query.filter(
        User.tier == 'trial',
        User.trial_ends_at <= two_days_later,
        User.trial_ends_at > now,
        User.trial_reminder_sent == False
    ).all()
    
    for user in trial_users:
        try:
            send_trial_reminder(user)
            user.trial_reminder_sent = True
            db.session.commit()
            logger.info(f"Trial reminder sent to {user.email}")
        except Exception as e:
            logger.error(f"Error sending trial reminder to {user.email}: {e}")
            db.session.rollback()
    
    # Находим пользователей у которых trial уже истёк
    expired_users = User.query.filter(
        User.tier == 'trial',
        User.trial_ends_at <= now
    ).all()
    
    for user in expired_users:
        try:
            user.tier = 'expired'
            db.session.commit()
            logger.info(f"Trial expired for {user.email}")
        except Exception as e:
            logger.error(f"Error expiring trial for {user.email}: {e}")
            db.session.rollback()

def send_trial_reminder(user):
    """Отправляет email напоминание об истекающем trial."""
    days_left = user.trial_days_left()
    
    subject = f"Ваш trial в Shipter заканчивается через {days_left} дн."
    
    body = f"""
Привет, {user.name or 'друг'}!

Ваш бесплатный trial период в Shipter заканчивается через {days_left} дн.

Не упустите возможность продолжить пользоваться всеми функциями:
- AI-анализ проектов
- Генерация контента
- Пошаговые планы дистрибуции

Выберите тариф который подходит именно вам:
{Config.APP_URL}/billing/plans

Если у вас есть вопросы — просто ответьте на это письмо.

Команда Shipter
"""
    
    try:
        msg = Message(
            subject=subject,
            recipients=[user.email],
            body=body
        )
        mail.send(msg)
    except Exception as e:
        logger.error(f"Error sending email to {user.email}: {e}")
        raise

def init_scheduler():
    """Инициализирует фоновые задачи."""
    # Запускаем проверку trial каждый день в 9 утра
    scheduler.add_job(
        check_trial_expirations,
        'cron',
        hour=9,
        minute=0,
        id='check_trial_expirations',
        replace_existing=True
    )
    
    if not scheduler.running:
        scheduler.start()
    logger.info("Scheduler initialized")
