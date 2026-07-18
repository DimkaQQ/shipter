from datetime import datetime, timezone
from app.extensions import db


class AdCreative(db.Model):
    __tablename__ = 'ad_creatives'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    format = db.Column(db.String(20), nullable=False)  # square | landscape | story
    headline = db.Column(db.String(255))
    svg_markup = db.Column(db.Text, nullable=False)
    tokens_used = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
