from datetime import datetime, timezone, date
from app.extensions import db

class ActionTask(db.Model):
    __tablename__ = 'action_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(500))
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # content | outreach | setup | analytics
    status = db.Column(db.String(20), default='pending')  # pending | in_progress | done | skipped
    due_date = db.Column(db.Date)
    ai_generated = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
