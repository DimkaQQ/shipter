from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify, current_app
from app.middleware.auth import login_required
from app.services.payment_service import create_checkout_session, get_subscription_status, cancel_subscription_at_period_end
from app.config import Config
from app.extensions import csrf

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/plans')
@login_required
def plans():
    user = g.current_user
    subscription_info = get_subscription_status(user)
    
    expired = request.args.get('expired', 'false').lower() == 'true'
    
    return render_template('billing/plans.html', 
                         subscription=subscription_info,
                         expired=expired,
                         stripe_key=Config.STRIPE_PUBLISHABLE_KEY)

@billing_bp.route('/checkout/<tier>')
@login_required
def checkout(tier):
    user = g.current_user
    
    if tier == 'starter':
        price_id = Config.STRIPE_PRICE_STARTER
    elif tier == 'pro':
        price_id = Config.STRIPE_PRICE_PRO
    else:
        flash('Неверный тариф', 'error')
        return redirect(url_for('billing.plans'))
    
    try:
        checkout_url = create_checkout_session(user, price_id, tier)
        return redirect(checkout_url)
    except Exception as e:
        flash(f'Ошибка создания платежа: {str(e)}', 'error')
        return redirect(url_for('billing.plans'))

@billing_bp.route('/success')
@login_required
def success():
    session_id = request.args.get('session_id')
    
    if not session_id:
        flash('Неверная ссылка', 'error')
        return redirect(url_for('billing.plans'))
    
    # В реальном приложении здесь можно проверить статус сессии через Stripe API
    # Но основная логика активации происходит в webhook
    
    flash('Подписка активирована! Добро пожаловать!', 'success')
    return render_template('billing/success.html')

@billing_bp.route('/webhook/stripe', methods=['POST'])
@csrf.exempt  # запрос приходит от Stripe, а не из браузерной сессии — CSRF-токена нет и не будет
def stripe_webhook():
    """Stripe webhook endpoint."""
    from app.services.payment_service import handle_webhook
    
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        handle_webhook(payload, sig_header)
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        current_app.logger.error(f"Webhook error: {e}")
        return jsonify({'error': str(e)}), 400

@billing_bp.route('/cancel', methods=['POST'])
@login_required
def cancel_subscription():
    """Отмена подписки — реальный вызов Stripe API (доступ до конца оплаченного периода)."""
    user = g.current_user
    subscription = (
        user.subscriptions.filter_by(status='active').first()
        or user.subscriptions.filter_by(status='past_due').first()
    )

    if not subscription:
        flash('Нет активной подписки', 'error')
        return redirect(url_for('billing.plans'))

    try:
        cancel_subscription_at_period_end(subscription)
        flash('Подписка будет отменена в конце периода', 'info')
    except Exception as e:
        current_app.logger.error(f"Cancel subscription error: {e}")
        flash('Не удалось отменить подписку. Попробуйте позже или напишите в поддержку.', 'error')

    return redirect(url_for('billing.plans'))
