import re
import time
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from app.extensions import db, redis_client, csrf
from app.models.project import Project
from app.models.subscriber import Subscriber
from app.middleware.auth import login_required, requires_pro

crm_bp = Blueprint('crm', __name__)

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
SIGNUP_RATE_LIMIT_PER_MINUTE = 20


def _signup_rate_limited(ip: str) -> bool:
    try:
        minute_bucket = time.strftime('%Y%m%d%H%M')
        key = f"ratelimit:signup:{ip}:{minute_bucket}"
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, 60)
        return count > SIGNUP_RATE_LIMIT_PER_MINUTE
    except Exception:
        return False


@crm_bp.route('/<int:project_id>')
@login_required
@requires_pro
def list_subscribers(project_id):
    user = g.current_user
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
    subscribers = project.subscribers.order_by(Subscriber.created_at.desc()).all()
    signup_url = url_for('crm.signup', project_id=project.id, _external=True)
    return render_template('crm/list.html', project=project, subscribers=subscribers, signup_url=signup_url)


@crm_bp.route('/<int:project_id>/add', methods=['POST'])
@login_required
@requires_pro
def add_subscriber(project_id):
    user = g.current_user
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()

    email = request.form.get('email', '').strip().lower()
    if not EMAIL_RE.match(email):
        flash('Введите корректный email', 'error')
        return redirect(url_for('crm.list_subscribers', project_id=project.id))

    existing = Subscriber.query.filter_by(project_id=project.id, email=email).first()
    if existing:
        flash('Этот email уже в списке', 'warning')
        return redirect(url_for('crm.list_subscribers', project_id=project.id))

    subscriber = Subscriber(project_id=project.id, email=email, source='manual')
    db.session.add(subscriber)
    db.session.commit()

    flash('Подписчик добавлен', 'success')
    return redirect(url_for('crm.list_subscribers', project_id=project.id))


@crm_bp.route('/subscriber/<int:subscriber_id>/delete', methods=['POST'])
@login_required
@requires_pro
def delete_subscriber(subscriber_id):
    user = g.current_user
    subscriber = Subscriber.query.join(Project).filter(
        Subscriber.id == subscriber_id, Project.user_id == user.id
    ).first_or_404()

    project_id = subscriber.project_id
    db.session.delete(subscriber)
    db.session.commit()

    flash('Подписчик удалён', 'success')
    return redirect(url_for('crm.list_subscribers', project_id=project_id))


@crm_bp.route('/<int:project_id>/signup', methods=['POST'])
@csrf.exempt  # публичная форма на сайте пользователя, без сессии/CSRF
def signup(project_id):
    """Публичная форма подписки — встраивается на сайт пользователя."""
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()

    if _signup_rate_limited(ip):
        return jsonify({'error': 'rate_limited'}), 429

    project = Project.query.filter_by(id=project_id).first()
    if not project:
        return jsonify({'error': 'unknown_project'}), 404

    email = request.form.get('email', '').strip().lower()
    if not EMAIL_RE.match(email):
        return jsonify({'error': 'invalid_email'}), 400

    existing = Subscriber.query.filter_by(project_id=project.id, email=email).first()
    if not existing:
        db.session.add(Subscriber(project_id=project.id, email=email, source='signup_form'))
        db.session.commit()

    return jsonify({'ok': True}), 201


@crm_bp.route('/unsubscribe/<token>')
@csrf.exempt
def unsubscribe(token):
    """Публичная страница отписки — ссылка на неё приходит в каждом письме рассылки."""
    subscriber = Subscriber.query.filter_by(unsubscribe_token=token).first_or_404()

    if subscriber.unsubscribed_at is None:
        subscriber.unsubscribed_at = datetime.now(timezone.utc)
        db.session.commit()

    return render_template('crm/unsubscribed.html')
