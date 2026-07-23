from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from redis import Redis
from apscheduler.schedulers.background import BackgroundScheduler
from authlib.integrations.flask_client import OAuth
from flask_wtf import CSRFProtect
from app.config import Config

db = SQLAlchemy()
mail = Mail()
redis_client = Redis.from_url(Config.REDIS_URL, decode_responses=True)
scheduler = BackgroundScheduler()
oauth = OAuth()
csrf = CSRFProtect()
