from app.routes.public import public_bp
from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.projects import projects_bp
from app.routes.ai import ai_bp
from app.routes.billing import billing_bp

__all__ = ['public_bp', 'auth_bp', 'dashboard_bp', 'projects_bp', 'ai_bp', 'billing_bp']
