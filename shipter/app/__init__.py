from flask import Flask, g, session
from datetime import datetime, timezone
from app.config import Config
from app.extensions import db, mail, redis_client, scheduler, oauth, csrf
from app.middleware.auth import load_user
import logging

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    oauth.init_app(app)
    if Config.GOOGLE_CLIENT_ID and Config.GOOGLE_CLIENT_SECRET:
        oauth.register(
            name='google',
            client_id=Config.GOOGLE_CLIENT_ID,
            client_secret=Config.GOOGLE_CLIENT_SECRET,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Register blueprints
    from app.routes.public import public_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.projects import projects_bp
    from app.routes.ai import ai_bp
    from app.routes.billing import billing_bp
    
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(projects_bp, url_prefix='/projects')
    app.register_blueprint(ai_bp, url_prefix='/ai')
    app.register_blueprint(billing_bp, url_prefix='/billing')
    
    # Load user before each request
    @app.before_request
    def before_request():
        load_user()
        if session.get('user_id'):
            session.permanent = True
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return 'Page not found', 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return 'Internal server error', 500
    
    return app
