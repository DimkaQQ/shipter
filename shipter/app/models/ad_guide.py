from datetime import datetime, timezone
from app.extensions import db


class AdGuide(db.Model):
    __tablename__ = 'ad_guides'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    recommended_platforms = db.Column(db.JSON)  # массив {platform, why, budget_share_percent}
    budget_plan = db.Column(db.Text)
    targeting = db.Column(db.Text)
    campaign_structure = db.Column(db.JSON)  # массив {step, description}
    creative_tips = db.Column(db.Text)
    sources = db.Column(db.JSON)  # массив {title, url}
    tokens_used = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
