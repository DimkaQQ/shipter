from flask import Flask, g, session
from datetime import datetime, timezone
from app.config import Config
from app.extensions import db, mail, redis_client, scheduler, oauth, csrf
from app.middleware.auth import load_user
import logging

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if Config.SENTRY_DSN:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        sentry_sdk.init(dsn=Config.SENTRY_DSN, integrations=[FlaskIntegration()], traces_sample_rate=0.1)

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
    if Config.META_APP_ID and Config.META_APP_SECRET:
        oauth.register(
            name='meta',
            client_id=Config.META_APP_ID,
            client_secret=Config.META_APP_SECRET,
            access_token_url=f'https://graph.facebook.com/{Config.META_API_VERSION}/oauth/access_token',
            authorize_url=f'https://www.facebook.com/{Config.META_API_VERSION}/dialog/oauth',
            client_kwargs={'scope': 'ads_management,pages_show_list,business_management'},
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
    from app.routes.integrations import integrations_bp
    from app.routes.tracking import tracking_bp
    from app.routes.crm import crm_bp
    from app.routes.meta_ads import meta_ads_bp
    from app.routes.settings import settings_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(projects_bp, url_prefix='/projects')
    app.register_blueprint(ai_bp, url_prefix='/ai')
    app.register_blueprint(billing_bp, url_prefix='/billing')
    app.register_blueprint(integrations_bp, url_prefix='/integrations')
    app.register_blueprint(tracking_bp)
    app.register_blueprint(crm_bp, url_prefix='/subscribers')
    app.register_blueprint(meta_ads_bp, url_prefix='/meta-ads')
    app.register_blueprint(settings_bp)
    
    # Load user before each request
    @app.before_request
    def before_request():
        load_user()
        if session.get('user_id'):
            session.permanent = True
    
    @app.route('/healthz')
    def healthz():
        from sqlalchemy import text
        checks = {}

        try:
            db.session.execute(text('SELECT 1'))
            checks['database'] = 'ok'
        except Exception as e:
            checks['database'] = f'error: {e}'

        try:
            redis_client.ping()
            checks['redis'] = 'ok'
        except Exception as e:
            checks['redis'] = f'error: {e}'

        healthy = checks['database'] == 'ok'
        return checks, 200 if healthy else 503

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return 'Page not found', 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return 'Internal server error', 500
    
    return app
