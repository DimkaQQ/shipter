from datetime import datetime, timezone
from app.extensions import db


class PublishLog(db.Model):
    __tablename__ = 'publish_logs'

    id = db.Column(db.Integer, primary_key=True)
    generated_content_id = db.Column(db.Integer, db.ForeignKey('generated_content.id', ondelete='CASCADE'), nullable=False)
    integration_id = db.Column(db.Integer, db.ForeignKey('integrations.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # success | failed
    error_message = db.Column(db.Text)
    published_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    integration = db.relationship('Integration')
    generated_content = db.relationship('GeneratedContent', backref=db.backref('publish_logs', lazy='dynamic', cascade='all, delete-orphan'))
