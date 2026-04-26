import stripe
import logging
from app.extensions import db
from app.config import Config
from app.models.subscription import Subscription
from app.models.user import User

logger = logging.getLogger(__name__)

stripe.api_key = Config.STRIPE_SECRET_KEY

def create_checkout_session(user, price_id: str, tier: str) -> str:
    """Возвращает URL для редиректа на Stripe Checkout."""
    try:
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email, 
                name=user.name,
                metadata={'user_id': user.id}
            )
            user.stripe_customer_id = customer.id
            db.session.commit()
        
        session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=f"{Config.APP_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{Config.APP_URL}/billing/plans",
            metadata={'user_id': user.id, 'tier': tier},
            subscription_data={'trial_period_days': 0},
        )
        return session.url
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        raise

def handle_webhook(payload: bytes, sig_header: str):
    """Обрабатывает Stripe webhooks."""
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, Config.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        raise
    
    logger.info(f"Processing webhook event: {event.type}")
    
    if event.type == 'checkout.session.completed':
        session = event.data.object
        _activate_subscription(session)
    
    elif event.type == 'customer.subscription.updated':
        sub = event.data.object
        _update_subscription(sub)
    
    elif event.type in ('customer.subscription.deleted', 'invoice.payment_failed'):
        sub = event.data.object
        _cancel_subscription(sub)
    
    else:
        logger.info(f"Unhandled event type: {event.type}")
    
    return event

def _activate_subscription(session):
    """Активирует подписку после успешной оплаты."""
    try:
        user_id = int(session.metadata.get('user_id'))
        tier = session.metadata.get('tier', 'starter')
        subscription_id = session.subscription
        
        # Получаем детали подписки
        stripe_sub = stripe.Subscription.retrieve(subscription_id)
        
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User not found: {user_id}")
            return
        
        # Обновляем пользователя
        user.tier = tier
        
        # Создаём или обновляем подписку
        existing_sub = Subscription.query.filter_by(stripe_subscription_id=subscription_id).first()
        
        if existing_sub:
            existing_sub.status = 'active'
            existing_sub.tier = tier
            existing_sub.current_period_start = stripe_sub.current_period_start
            existing_sub.current_period_end = stripe_sub.current_period_end
        else:
            new_sub = Subscription(
                user_id=user.id,
                stripe_subscription_id=subscription_id,
                stripe_price_id=stripe_sub.items.data[0].price.id,
                tier=tier,
                status='active',
                current_period_start=stripe_sub.current_period_start,
                current_period_end=stripe_sub.current_period_end,
            )
            db.session.add(new_sub)
        
        db.session.commit()
        logger.info(f"Subscription activated for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error activating subscription: {e}")
        db.session.rollback()
        raise

def _update_subscription(stripe_sub):
    """Обновляет подписку при изменениях."""
    try:
        sub = Subscription.query.filter_by(stripe_subscription_id=stripe_sub.id).first()
        if not sub:
            logger.warning(f"Subscription not found: {stripe_sub.id}")
            return
        
        sub.status = stripe_sub.status
        sub.cancel_at_period_end = stripe_sub.cancel_at_period_end
        sub.current_period_start = stripe_sub.current_period_start
        sub.current_period_end = stripe_sub.current_period_end
        
        # Если подписка отменена, проверяем не истёк ли период
        if stripe_sub.status == 'active' and not stripe_sub.cancel_at_period_end:
            user = User.query.get(sub.user_id)
            if user:
                user.tier = sub.tier
        
        db.session.commit()
        logger.info(f"Subscription updated: {stripe_sub.id}")
        
    except Exception as e:
        logger.error(f"Error updating subscription: {e}")
        db.session.rollback()
        raise

def _cancel_subscription(stripe_sub):
    """Отменяет подписку."""
    try:
        sub = Subscription.query.filter_by(stripe_subscription_id=stripe_sub.id).first()
        if not sub:
            logger.warning(f"Subscription not found: {stripe_sub.id}")
            return
        
        sub.status = 'cancelled'
        sub.cancel_at_period_end = True
        
        # Помечаем пользователя как expired
        user = User.query.get(sub.user_id)
        if user:
            user.tier = 'expired'
        
        db.session.commit()
        logger.info(f"Subscription cancelled: {stripe_sub.id}")
        
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        db.session.rollback()
        raise

def get_subscription_status(user) -> dict:
    """Возвращает статус подписки пользователя."""
    subscription = user.subscriptions.filter_by(status='active').first()
    
    if not subscription:
        return {
            'active': False,
            'tier': user.tier,
            'trial_days_left': user.trial_days_left(),
            'is_trial': user.tier == 'trial'
        }
    
    return {
        'active': True,
        'tier': subscription.tier,
        'current_period_end': subscription.current_period_end,
        'cancel_at_period_end': subscription.cancel_at_period_end
    }
