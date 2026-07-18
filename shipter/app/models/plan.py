from datetime import datetime, timezone
from app.extensions import db

class DistributionPlan(db.Model):
    __tablename__ = 'distribution_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    niche_analysis = db.Column(db.Text)
    competitors = db.Column(db.JSON)  # массив {name, pros, cons}
    monetization = db.Column(db.JSON)  # массив {title, description, price, reasoning}
    distribution_steps = db.Column(db.JSON)  # массив {week, actions[]}
    quick_wins = db.Column(db.JSON)  # массив {action, impact, effort, time}
    main_advice = db.Column(db.Text)
    sources = db.Column(db.JSON)  # массив {title, url} — найдено через веб-поиск
    tokens_used = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
