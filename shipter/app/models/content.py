from datetime import datetime, timezone
from app.extensions import db

class GeneratedContent(db.Model):
    __tablename__ = 'generated_content'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    type = db.Column(db.String(50))  # telegram_post | twitter_post | product_desc | landing_hero | email_sequence | cold_outreach
    content = db.Column(db.Text, nullable=False)
    tokens_used = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
