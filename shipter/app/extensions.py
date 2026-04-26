from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from redis import Redis
from apscheduler.schedulers.background import BackgroundScheduler

db = SQLAlchemy()
mail = Mail()
redis_client = Redis.from_url('redis://localhost:6379/0', decode_responses=True)
scheduler = BackgroundScheduler()
