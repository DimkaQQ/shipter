import json
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, session, Response
from app.extensions import db
from app.middleware.auth import login_required
from app.services.data_export_service import build_user_export

logger = logging.getLogger(__name__)
settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/settings')
@login_required
def index():
    return render_template('settings/index.html')


@settings_bp.route('/settings/export')
@login_required
def export_data():
    data = build_user_export(g.current_user)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    return Response(
        payload,
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment; filename=shipter-data-export.json'},
    )


@settings_bp.route('/settings/delete', methods=['POST'])
@login_required
def delete_account():
    user = g.current_user
    confirm_email = request.form.get('confirm_email', '').strip().lower()

    if confirm_email != user.email.lower():
        flash('Email не совпадает. Аккаунт не удалён.', 'error')
        return redirect(url_for('settings.index'))

    try:
        active_sub = (
            user.subscriptions.filter_by(status='active').first()
            or user.subscriptions.filter_by(status='past_due').first()
        )
        if active_sub and active_sub.stripe_subscription_id:
            from app.services.payment_service import cancel_subscription_now
            cancel_subscription_now(active_sub)
    except Exception as e:
        logger.error(f"Error cancelling subscription during account deletion: {e}")

    user_id = user.id
    db.session.delete(user)
    db.session.commit()
    session.clear()

    logger.info(f"Account deleted: user_id={user_id}")
    flash('Аккаунт и все данные удалены.', 'info')
    return redirect(url_for('public.landing'))
