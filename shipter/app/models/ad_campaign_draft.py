from datetime import datetime, timezone
from app.extensions import db


class AdCampaignDraft(db.Model):
    __tablename__ = 'ad_campaign_drafts'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    platform = db.Column(db.String(20), nullable=False, default='meta')
    name = db.Column(db.String(255), nullable=False)
    daily_budget = db.Column(db.Numeric(10, 2))
    country = db.Column(db.String(2))
    external_campaign_id = db.Column(db.String(64))
    external_adset_id = db.Column(db.String(64))
    status = db.Column(db.String(20), default='draft_created')  # draft_created | failed
    error_message = db.Column(db.Text)
    ads_manager_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
