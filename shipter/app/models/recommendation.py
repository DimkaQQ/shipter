from datetime import datetime, timezone
from app.extensions import db


class Recommendation(db.Model):
    __tablename__ = 'recommendations'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    services = db.Column(db.JSON)  # массив {name, category, why_fits, url}
    hubs = db.Column(db.JSON)      # массив {name, region, why_fits, url, offer_summary}
    tokens_used = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
