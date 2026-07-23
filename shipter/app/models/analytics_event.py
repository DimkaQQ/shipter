from datetime import datetime, timezone
from app.extensions import db


class AnalyticsEvent(db.Model):
    __tablename__ = 'analytics_events'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    event_type = db.Column(db.String(20), nullable=False, default='pageview')
    path = db.Column(db.String(500))
    referrer = db.Column(db.String(500))
    visitor_hash = db.Column(db.String(64))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
