from functools import wraps
from flask import redirect, url_for, g, session, flash
from app.models.user import User
from datetime import datetime, timezone

def load_user():
    """Загружает текущего пользователя из сессии в g.current_user."""
    g.current_user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            user.last_seen = datetime.now(timezone.utc)
            g.current_user = user

def login_required(f):
    """Декоратор требующий авторизации."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or g.current_user is None:
            flash('Пожалуйста, войдите чтобы продолжить', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def requires_active_subscription(f):
    """Декоратор требующий активную подписку или trial."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = g.current_user
        if not user.is_active():
            flash('Ваша подписка истекла. Пожалуйста, выберите тариф для продолжения.', 'warning')
            return redirect(url_for('billing.plans', expired='true'))
        return f(*args, **kwargs)
    return decorated

def requires_pro(f):
    """Декоратор требующий Pro план."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = g.current_user
        if user.tier != 'pro' or not user.is_active():
            flash('Эта функция доступна только на Pro плане', 'warning')
            return redirect(url_for('billing.plans'))
        return f(*args, **kwargs)
    return decorated
