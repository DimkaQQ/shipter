from datetime import datetime, timezone, timedelta
from app.extensions import db
import bcrypt

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    name = db.Column(db.String(255))
    google_id = db.Column(db.String(255), unique=True)
    avatar_url = db.Column(db.String(500))
    email_verified = db.Column(db.Boolean, default=False)
    email_verify_token = db.Column(db.String(255))
    tier = db.Column(db.String(20), default='trial')
    trial_ends_at = db.Column(db.DateTime(timezone=True))
    trial_reminder_sent = db.Column(db.Boolean, default=False)
    stripe_customer_id = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    projects = db.relationship('Project', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    subscriptions = db.relationship('Subscription', backref='user', lazy='dynamic')

    def set_password(self, password: str):
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())

    def is_active(self) -> bool:
        if self.tier in ('starter', 'pro'):
            sub = self.subscriptions.filter_by(status='active').first()
            return sub is not None
        if self.tier == 'trial':
            return self.trial_ends_at and datetime.now(timezone.utc) < self.trial_ends_at
        return False

    def trial_days_left(self) -> int | None:
        if self.tier != 'trial':
            return None
        if not self.trial_ends_at:
            return 0
        delta = self.trial_ends_at - datetime.now(timezone.utc)
        return max(0, delta.days)

    def has_feature(self, feature: str) -> bool:
        """Проверка доступа к фиче по тарифу."""
        FEATURES = {
            'ai_analyze':      ['trial', 'starter', 'pro'],
            'ai_generate':     ['trial', 'starter', 'pro'],
            'action_tasks':    ['pro'],           # только $199 план
            'unlimited_projects': ['pro'],
            'priority_support': ['pro'],
            'ad_creatives':    ['starter', 'pro'],  # базовые SVG-баннеры, не на trial
        }
        allowed_tiers = FEATURES.get(feature, [])
        return self.tier in allowed_tiers and self.is_active()

    @classmethod
    def create_with_trial(cls, email: str, password: str = None, name: str = None, google_id: str = None):
        from app.config import Config
        user = cls(
            email=email,
            name=name,
            google_id=google_id,
            tier='trial',
            trial_ends_at=datetime.now(timezone.utc) + timedelta(days=Config.TRIAL_DAYS),
            email_verified=bool(google_id),  # Google уже верифицировал
        )
        if password:
            user.set_password(password)
        return user
