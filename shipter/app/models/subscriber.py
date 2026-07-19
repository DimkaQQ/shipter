import secrets
from datetime import datetime, timezone
from app.extensions import db


class Subscriber(db.Model):
    __tablename__ = 'subscribers'
    __table_args__ = (
        db.UniqueConstraint('project_id', 'email', name='uq_subscriber_project_email'),
    )

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    source = db.Column(db.String(20), default='manual')  # manual | signup_form
    unsubscribe_token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32))
    unsubscribed_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    project = db.relationship('Project', backref=db.backref('subscribers', lazy='dynamic', cascade='all, delete-orphan'))

    @property
    def is_active(self) -> bool:
        return self.unsubscribed_at is None
