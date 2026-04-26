from flask import Blueprint, render_template, g, redirect, url_for
from app.middleware.auth import login_required
from app.models.project import Project
from app.models.generated_content import GeneratedContent
from app.models.action_task import ActionTask
from datetime import date

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    user = g.current_user
    
    # Получаем проекты пользователя
    projects = user.projects.order_by(Project.created_at.desc()).limit(5).all()
    
    # Последние генерации контента
    recent_content = GeneratedContent.query.filter_by(user_id=user.id).order_by(GeneratedContent.created_at.desc()).limit(3).all()
    
    # Задачи на сегодня (только Pro)
    today_tasks = []
    if user.tier == 'pro':
        today_tasks = ActionTask.query.filter_by(
            user_id=user.id, 
            status='pending',
            due_date=date.today()
        ).all()
    
    return render_template('dashboard/index.html', 
                         projects=projects, 
                         recent_content=recent_content,
                         today_tasks=today_tasks)
