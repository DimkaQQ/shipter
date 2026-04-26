from datetime import datetime, timezone
from app.extensions import db

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50))  # saas | bot | app | content | service | other
    audience = db.Column(db.Text)
    problem = db.Column(db.Text)
    website_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    distribution_plan = db.relationship('DistributionPlan', backref='project', uselist=False, cascade='all, delete-orphan')
    generated_content = db.relationship('GeneratedContent', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    action_tasks = db.relationship('ActionTask', backref='project', lazy='dynamic', cascade='all, delete-orphan')
