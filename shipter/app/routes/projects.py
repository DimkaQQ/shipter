from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from sqlalchemy import func
from app.extensions import db
from app.models.project import Project
from app.models.action_task import ActionTask
from app.models.generated_content import GeneratedContent
from app.models.recommendation import Recommendation
from app.models.analytics_event import AnalyticsEvent
from app.middleware.auth import login_required, requires_active_subscription
from datetime import datetime, timezone, date, timedelta

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/')
@login_required
def list_projects():
    user = g.current_user
    projects = user.projects.order_by(Project.created_at.desc()).all()
    
    # Проверка лимита проектов
    max_projects = 3 if user.tier == 'trial' else (5 if user.tier == 'starter' else None)
    
    return render_template('projects/list.html', projects=projects, max_projects=max_projects)

@projects_bp.route('/create', methods=['GET', 'POST'])
@login_required
@requires_active_subscription
def create_project():
    user = g.current_user
    
    # Проверка лимита проектов
    max_projects = 3 if user.tier == 'trial' else (5 if user.tier == 'starter' else None)
    if max_projects and user.projects.count() >= max_projects:
        flash(f'Вы достигли лимита проектов ({max_projects}). Upgrade до Pro для безлимита.', 'warning')
        return redirect(url_for('billing.plans'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        project_type = request.form.get('type', 'other')
        audience = request.form.get('audience', '').strip()
        problem = request.form.get('problem', '').strip()
        website_url = request.form.get('website_url', '').strip()
        
        if not name or not description:
            flash('Название и описание обязательны', 'error')
            return render_template('projects/create.html')
        
        project = Project(
            user_id=user.id,
            name=name,
            description=description,
            type=project_type,
            audience=audience or None,
            problem=problem or None,
            website_url=website_url or None
        )
        
        db.session.add(project)
        db.session.commit()
        
        flash('Проект создан!', 'success')
        return redirect(url_for('projects.detail', project_id=project.id))
    
    return render_template('projects/create.html')

@projects_bp.route('/<int:project_id>')
@login_required
@requires_active_subscription
def detail(project_id):
    user = g.current_user
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
    
    # Получаем связанные данные
    plan = project.distribution_plan
    content_items = project.generated_content.order_by(GeneratedContent.created_at.desc()).all()
    tasks = project.action_tasks.order_by(ActionTask.due_date).all() if user.tier == 'pro' else []
    recommendation = Recommendation.query.filter_by(project_id=project.id).order_by(Recommendation.created_at.desc()).first()
    integrations = project.integrations.filter_by(is_active=True).all() if user.tier == 'pro' else []
    analytics = _project_analytics(project.id)

    return render_template('projects/detail.html',
                         project=project,
                         plan=plan,
                         content_items=content_items,
                         recommendation=recommendation,
                         integrations=integrations,
                         analytics=analytics,
                         tasks=tasks)


def _project_analytics(project_id: int) -> dict:
    """Агрегированная статистика встраиваемого счётчика для вкладки 'Аналитика'."""
    base = AnalyticsEvent.query.filter_by(project_id=project_id)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    total_pageviews = base.count()
    pageviews_30d = base.filter(AnalyticsEvent.created_at >= thirty_days_ago).count()
    unique_visitors_30d = base.filter(AnalyticsEvent.created_at >= thirty_days_ago) \
        .with_entities(func.count(func.distinct(AnalyticsEvent.visitor_hash))).scalar() or 0

    top_paths = base.filter(AnalyticsEvent.created_at >= thirty_days_ago) \
        .with_entities(AnalyticsEvent.path, func.count(AnalyticsEvent.id).label('cnt')) \
        .group_by(AnalyticsEvent.path).order_by(func.count(AnalyticsEvent.id).desc()).limit(5).all()

    top_referrers = base.filter(AnalyticsEvent.created_at >= thirty_days_ago, AnalyticsEvent.referrer != '') \
        .with_entities(AnalyticsEvent.referrer, func.count(AnalyticsEvent.id).label('cnt')) \
        .group_by(AnalyticsEvent.referrer).order_by(func.count(AnalyticsEvent.id).desc()).limit(5).all()

    return {
        'total_pageviews': total_pageviews,
        'pageviews_30d': pageviews_30d,
        'unique_visitors_30d': unique_visitors_30d,
        'top_paths': top_paths,
        'top_referrers': top_referrers,
    }

@projects_bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
@requires_active_subscription
def edit_project(project_id):
    user = g.current_user
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
    
    if request.method == 'POST':
        project.name = request.form.get('name', '').strip()
        project.description = request.form.get('description', '').strip()
        project.type = request.form.get('type', 'other')
        project.audience = request.form.get('audience', '').strip() or None
        project.problem = request.form.get('problem', '').strip() or None
        project.website_url = request.form.get('website_url', '').strip() or None
        project.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        flash('Проект обновлён', 'success')
        return redirect(url_for('projects.detail', project_id=project.id))
    
    return render_template('projects/edit.html', project=project)

@projects_bp.route('/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    user = g.current_user
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
    
    db.session.delete(project)
    db.session.commit()
    
    flash('Проект удалён', 'success')
    return redirect(url_for('projects.list_projects'))

@projects_bp.route('/<int:project_id>/add-task', methods=['POST'])
@login_required
def add_task(project_id):
    """Добавить задачу в проект (Pro only)."""
    user = g.current_user
    
    if user.tier != 'pro':
        flash('Функция доступна только для Pro тарифа', 'error')
        return redirect(url_for('projects.detail', project_id=project_id))
    
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
    
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category', 'content')
    due_date_str = request.form.get('due_date', '')
    
    if not title:
        flash('Название задачи обязательно', 'error')
        return redirect(url_for('projects.detail', project_id=project_id))
    
    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    task = ActionTask(
        project_id=project.id,
        user_id=user.id,
        title=title,
        description=description or None,
        category=category,
        due_date=due_date,
        ai_generated=False
    )
    
    db.session.add(task)
    db.session.commit()
    
    flash('Задача добавлена', 'success')
    return redirect(url_for('projects.detail', project_id=project_id))

@projects_bp.route('/task/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task(task_id):
    """Переключить статус задачи (Pro only)."""
    user = g.current_user
    
    if user.tier != 'pro':
        return jsonify({'error': 'Forbidden'}), 403
    
    task = ActionTask.query.filter_by(id=task_id, user_id=user.id).first_or_404()
    
    data = request.get_json()
    new_status = data.get('status', 'pending')
    
    if new_status not in ('pending', 'in_progress', 'done', 'skipped'):
        return jsonify({'error': 'Invalid status'}), 400
    
    task.status = new_status
    db.session.commit()
    
    return jsonify({'success': True, 'status': task.status})

@projects_bp.route('/task/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    """Удалить задачу (Pro only)."""
    user = g.current_user
    
    if user.tier != 'pro':
        flash('Функция доступна только для Pro тарифа', 'error')
        return redirect(url_for('dashboard.index'))
    
    task = ActionTask.query.filter_by(id=task_id, user_id=user.id).first_or_404()
    
    project_id = task.project_id
    db.session.delete(task)
    db.session.commit()
    
    flash('Задача удалена', 'success')
    return redirect(url_for('projects.detail', project_id=project_id))
