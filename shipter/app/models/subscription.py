from datetime import datetime, timezone
from app.extensions import db

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    stripe_subscription_id = db.Column(db.String(255), unique=True)
    stripe_price_id = db.Column(db.String(255))
    tier = db.Column(db.String(20))  # starter | pro
    status = db.Column(db.String(20))  # active | cancelled | past_due | unpaid
    current_period_start = db.Column(db.DateTime(timezone=True))
    current_period_end = db.Column(db.DateTime(timezone=True))
    cancel_at_period_end = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
