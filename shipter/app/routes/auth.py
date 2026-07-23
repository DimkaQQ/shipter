from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from app.extensions import db, redis_client
from app.models.user import User
from app.middleware.auth import login_required
from app.extensions import oauth
from app.config import Config
import secrets
import time
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

RESET_RATE_LIMIT_PER_HOUR = 5
LOGIN_RATE_LIMIT_PER_15MIN = 10
RESEND_VERIFY_RATE_LIMIT_PER_HOUR = 5


def _resend_verify_rate_limited(ip: str) -> bool:
    try:
        hour_bucket = time.strftime('%Y%m%d%H')
        key = f"ratelimit:resend-verify:{ip}:{hour_bucket}"
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, 3600)
        return count > RESEND_VERIFY_RATE_LIMIT_PER_HOUR
    except Exception:
        # Redis недоступен — не блокируем повторную отправку из-за инфраструктурной ошибки
        return False


def _reset_rate_limited(ip: str) -> bool:
    try:
        hour_bucket = time.strftime('%Y%m%d%H')
        key = f"ratelimit:reset:{ip}:{hour_bucket}"
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, 3600)
        return count > RESET_RATE_LIMIT_PER_HOUR
    except Exception:
        # Redis недоступен — не блокируем восстановление пароля из-за инфраструктурной ошибки
        return False


def _login_blocked(ip: str) -> bool:
    """Проверяет, не превышен ли лимит неудачных попыток входа с этого IP."""
    try:
        window_bucket = int(time.time() // 900)  # окно 15 минут
        key = f"ratelimit:login:{ip}:{window_bucket}"
        count = redis_client.get(key)
        return bool(count) and int(count) >= LOGIN_RATE_LIMIT_PER_15MIN
    except Exception:
        return False


def _register_failed_login(ip: str) -> None:
    """Учитывает неудачную попытку входа с этого IP (окно 15 минут)."""
    try:
        window_bucket = int(time.time() // 900)
        key = f"ratelimit:login:{ip}:{window_bucket}"
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, 900)
    except Exception:
        # Redis недоступен — не блокируем вход из-за инфраструктурной ошибки
        pass

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if g.current_user:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()

        if _login_blocked(ip):
            flash('Слишком много неудачных попыток входа. Попробуйте снова через 15 минут.', 'error')
            return render_template('auth/login.html'), 429

        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Введите email и пароль', 'error')
            return render_template('auth/login.html')

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            _register_failed_login(ip)
            flash('Неверный email или пароль', 'error')
            return render_template('auth/login.html')

        if not user.email_verified:
            flash('Пожалуйста, подтвердите email перед входом. Не пришло письмо? '
                  'Ссылка для повторной отправки — под формой входа.', 'warning')
            return render_template('auth/login.html')

        session['user_id'] = user.id
        session.permanent = True
        flash(f'С возвращением, {user.name or "друг"}!', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if g.current_user:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        name = request.form.get('name', '').strip()
        
        if not email or not password:
            flash('Введите email и пароль', 'error')
            return render_template('auth/register.html')
        
        if len(password) < 8:
            flash('Пароль должен быть не менее 8 символов', 'error')
            return render_template('auth/register.html')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Этот email уже зарегистрирован', 'error')
            return render_template('auth/register.html')
        
        # Создаём пользователя с trial
        user = User.create_with_trial(email=email, password=password, name=name)
        user.email_verify_token = secrets.token_urlsafe(32)
        
        db.session.add(user)
        db.session.commit()
        
        # Отправляем email верификации
        try:
            send_verification_email(user)
            flash('Аккаунт создан! Проверьте почту для подтверждения.', 'success')
        except Exception as e:
            logger.error(f"Error sending verification email: {e}")
            flash('Аккаунт создан, но письмо не отправлено. Попробуйте позже.', 'warning')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/verify/<token>')
def verify_email(token):
    user = User.query.filter_by(email_verify_token=token).first()
    
    if not user:
        flash('Неверная ссылка подтверждения', 'error')
        return redirect(url_for('auth.login'))
    
    user.email_verified = True
    user.email_verify_token = None
    db.session.commit()
    
    flash('Email подтверждён! Теперь вы можете войти.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/resend-verification', methods=['GET', 'POST'])
def resend_verification():
    if g.current_user:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()

        if _resend_verify_rate_limited(ip):
            flash('Слишком много попыток. Попробуйте позже.', 'error')
            return render_template('auth/resend_verification.html')

        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first() if email else None

        # Одинаковый ответ независимо от результата — не раскрываем регистрацию email
        # и не спамим уже подтверждённых пользователей повторной отправкой.
        if user and not user.email_verified and user.password_hash:
            if not user.email_verify_token:
                user.email_verify_token = secrets.token_urlsafe(32)
                db.session.commit()
            try:
                send_verification_email(user)
            except Exception as e:
                logger.error(f"Error resending verification email: {e}")

        flash('Если этот email зарегистрирован и ещё не подтверждён, мы отправили письмо повторно.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/resend_verification.html')

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if g.current_user:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()

        if _reset_rate_limited(ip):
            flash('Слишком много попыток. Попробуйте позже.', 'error')
            return render_template('auth/forgot_password.html')

        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first() if email else None

        # Одинаковый ответ независимо от того, найден email или нет —
        # чтобы форма не раскрывала, зарегистрирован ли адрес.
        if user and user.password_hash:
            user.generate_reset_token()
            db.session.commit()
            try:
                send_reset_email(user)
            except Exception as e:
                logger.error(f"Error sending reset email: {e}")

        flash('Если этот email зарегистрирован, мы отправили на него ссылку для сброса пароля.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if g.current_user:
        return redirect(url_for('dashboard.index'))

    user = User.query.filter_by(reset_token=token).first()

    if not user or not user.reset_token_valid():
        flash('Ссылка для сброса пароля недействительна или устарела', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')

        if len(password) < 8:
            flash('Пароль должен быть не менее 8 символов', 'error')
            return render_template('auth/reset_password.html', token=token)

        user.set_password(password)
        user.reset_token = None
        user.reset_token_expires_at = None
        db.session.commit()

        flash('Пароль изменён. Теперь вы можете войти.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)

@auth_bp.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Вы вышли из аккаунта', 'info')
    return redirect(url_for('public.landing'))

@auth_bp.route('/google')
def google_login():
    """Инициирует Google OAuth flow."""
    if not hasattr(oauth, 'google'):
        flash('Вход через Google временно недоступен', 'error')
        return redirect(url_for('auth.login'))

    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/google/callback')
def google_callback():
    """Обрабатывает callback от Google OAuth."""
    if not hasattr(oauth, 'google'):
        flash('Вход через Google временно недоступен', 'error')
        return redirect(url_for('auth.login'))

    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info:
            flash('Ошибка авторизации через Google', 'error')
            return redirect(url_for('auth.login'))
        
        google_id = user_info.get('sub')
        email = user_info.get('email', '').lower()
        name = user_info.get('name')
        avatar = user_info.get('picture')
        
        # Проверяем существует ли пользователь с таким google_id
        user = User.query.filter_by(google_id=google_id).first()
        
        if user:
            # Существующий пользователь с Google
            session['user_id'] = user.id
            flash(f'С возвращением, {user.name or "друг"}!', 'success')
            return redirect(url_for('dashboard.index'))
        
        # Проверяем существует ли пользователь с таким email
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Связываем существующий аккаунт с Google
            user.google_id = google_id
            user.avatar_url = avatar
            if not user.name:
                user.name = name
            db.session.commit()
            session['user_id'] = user.id
            flash('Google аккаунт привязан!', 'success')
            return redirect(url_for('dashboard.index'))
        
        # Создаём нового пользователя
        user = User.create_with_trial(email=email, name=name, google_id=google_id)
        user.avatar_url = avatar
        db.session.add(user)
        db.session.commit()
        
        session['user_id'] = user.id
        flash('Добро пожаловать в Shipter!', 'success')
        return redirect(url_for('dashboard.index'))
        
    except Exception as e:
        logger.error(f"Google OAuth error: {e}")
        flash('Ошибка авторизации через Google', 'error')
        return redirect(url_for('auth.login'))

def send_verification_email(user):
    """Отправляет email для подтверждения почты."""
    from flask_mail import Message
    from app.extensions import mail
    
    verify_url = url_for('auth.verify_email', token=user.email_verify_token, _external=True)
    
    subject = "Подтвердите email в Shipter"
    body = f"""
Привет, {user.name or 'друг'}!

Спасибо за регистрацию в Shipter. 

Подтвердите свой email перейдя по ссылке:
{verify_url}

Если вы не регистрировались — просто проигнорируйте это письмо.

Команда Shipter
"""
    
    msg = Message(subject=subject, recipients=[user.email], body=body)
    mail.send(msg)

def send_reset_email(user):
    """Отправляет email со ссылкой для сброса пароля."""
    from flask_mail import Message
    from app.extensions import mail

    reset_url = url_for('auth.reset_password', token=user.reset_token, _external=True)

    subject = "Восстановление пароля Shipter"
    body = f"""
Привет, {user.name or 'друг'}!

Мы получили запрос на сброс пароля для вашего аккаунта в Shipter.

Перейдите по ссылке, чтобы задать новый пароль (ссылка действует 1 час):
{reset_url}

Если вы не запрашивали сброс пароля — просто проигнорируйте это письмо, ваш пароль останется прежним.

Команда Shipter
"""

    msg = Message(subject=subject, recipients=[user.email], body=body)
    mail.send(msg)
