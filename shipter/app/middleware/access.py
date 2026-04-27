from functools import wraps
from flask import redirect, url_for, g, flash


def requires_active_subscription(f):
    """
    Декоратор для проверки активной подписки или триала.
    Если у пользователя нет активной подписки и триал истёк — редирект на страницу тарифов.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        user = g.current_user
        if not user:
            return redirect(url_for('auth.login'))
        
        if not user.is_active():
            flash('Ваш пробный период истёк. Пожалуйста, выберите тариф для продолжения.', 'warning')
            return redirect(url_for('billing.plans'))
        
        return f(*args, **kwargs)
    return decorated


def requires_pro(f):
    """
    Декоратор для проверки Pro-подписки.
    Доступно только пользователям с тарифом 'pro'.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        user = g.current_user
        if not user:
            return redirect(url_for('auth.login'))
        
        if user.tier != 'pro':
            # Проверяем активную подписку
            if not user.is_active():
                flash('Ваш пробный период истёк. Пожалуйста, выберите тариф.', 'warning')
                return redirect(url_for('billing.plans'))
            else:
                flash('Эта функция доступна только в тарифе Pro.', 'info')
                return redirect(url_for('dashboard.index'))
        
        return f(*args, **kwargs)
    return decorated


# Алиасы для совместимости с импортами
login_required = requires_active_subscription
