import hashlib
import time
from datetime import date
from flask import Blueprint, request, jsonify
from app.extensions import db, redis_client, csrf
from app.config import Config
from app.models.project import Project
from app.models.analytics_event import AnalyticsEvent

tracking_bp = Blueprint('tracking', __name__)
csrf.exempt(tracking_bp)  # публичный эндпоинт для стороннего сайта пользователя, без сессии/CSRF

RATE_LIMIT_PER_MINUTE = 60


def _rate_limited(ip: str) -> bool:
    try:
        minute_bucket = time.strftime('%Y%m%d%H%M')
        key = f"ratelimit:track:{ip}:{minute_bucket}"
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, 60)
        return count > RATE_LIMIT_PER_MINUTE
    except Exception:
        # Redis недоступен — не блокируем сбор аналитики из-за инфраструктурной ошибки
        return False


@tracking_bp.route('/t/collect', methods=['POST', 'OPTIONS'])
def collect():
    if request.method == 'OPTIONS':
        resp = jsonify({})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()

    if _rate_limited(ip):
        resp = jsonify({'error': 'rate_limited'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 429

    data = request.get_json(silent=True) or {}
    project_id = data.get('project_id')

    project = Project.query.filter_by(id=project_id).first() if project_id else None
    if not project:
        resp = jsonify({'error': 'unknown_project'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 404

    user_agent = request.headers.get('User-Agent', '')
    visitor_raw = f"{ip}:{user_agent}:{date.today().isoformat()}:{Config.SECRET_KEY}"
    visitor_hash = hashlib.sha256(visitor_raw.encode()).hexdigest()

    event = AnalyticsEvent(
        project_id=project.id,
        event_type='pageview',
        path=(data.get('path') or '')[:500],
        referrer=(data.get('referrer') or '')[:500],
        visitor_hash=visitor_hash,
    )
    db.session.add(event)
    db.session.commit()

    resp = jsonify({'ok': True})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp, 204
