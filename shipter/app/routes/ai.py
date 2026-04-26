from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from app.extensions import db
from app.models.project import Project
from app.models.plan import DistributionPlan
from app.models.content import GeneratedContent
from app.models.action_task import ActionTask
from app.middleware.auth import login_required, requires_active_subscription, requires_pro
from app.services.ai_service import ai_service
from datetime import datetime, timezone, date

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/analyze/<int:project_id>', methods=['GET', 'POST'])
@login_required
@requires_active_subscription
def analyze_project(project_id):
    user = g.current_user
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
    
    # Если уже есть анализ - показываем его
    existing_plan = DistributionPlan.query.filter_by(project_id=project.id).first()
    if existing_plan and request.method == 'GET':
        return render_template('ai/analyze.html', project=project, plan=existing_plan)
    
    if request.method == 'POST':
        # Вызываем AI сервис
        result, from_cache = ai_service.analyze_project(project)
        
        # Сохраняем в БД
        plan = DistributionPlan(
            project_id=project.id,
            niche_analysis=result.get('niche_analysis', ''),
            competitors=result.get('competitors', []),
            monetization=result.get('monetization', []),
            distribution_steps=result.get('distribution_steps', []),
            quick_wins=result.get('quick_wins', []),
            main_advice=result.get('main_advice', ''),
            tokens_used=result.get('tokens_used', 0)
        )
        
        if existing_plan:
            db.session.delete(existing_plan)
        
        db.session.add(plan)
        db.session.commit()
        
        flash('AI-анализ завершён!', 'success')
        return redirect(url_for('projects.detail', project_id=project.id))
    
    return render_template('ai/analyze.html', project=project, plan=None)

@ai_bp.route('/generate/<int:project_id>', methods=['GET', 'POST'])
@login_required
@requires_active_subscription
def generate_content(project_id):
    user = g.current_user
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
    
    content_types = [
        ('telegram_post', 'Telegram пост'),
        ('twitter_post', 'Twitter/X пост'),
        ('product_desc', 'Описание продукта'),
        ('landing_hero', 'Hero секция лендинга'),
        ('email_sequence', 'Email последовательность'),
        ('cold_outreach', 'Cold outreach шаблон')
    ]
    
    if request.method == 'POST':
        content_type = request.form.get('content_type')
        
        if not content_type or content_type not in [t[0] for t in content_types]:
            flash('Выберите тип контента', 'error')
            return render_template('ai/generate.html', project=project, content_types=content_types)
        
        # Генерируем контент
        content, tokens_used = ai_service.generate_content(project, content_type)
        
        # Сохраняем
        generated = GeneratedContent(
            project_id=project.id,
            user_id=user.id,
            type=content_type,
            content=content,
            tokens_used=tokens_used
        )
        db.session.add(generated)
        db.session.commit()
        
        flash(f'{dict(content_types)[content_type]} сгенерирован!', 'success')
        return redirect(url_for('projects.detail', project_id=project.id))
    
    # Получаем已有的 генерации
    content_items = GeneratedContent.query.filter_by(project_id=project.id).order_by(GeneratedContent.created_at.desc()).all()
    
    return render_template('ai/generate.html', project=project, content_types=content_types, content_items=content_items)

@ai_bp.route('/tasks/<int:project_id>/generate', methods=['POST'])
@login_required
@requires_pro
def generate_tasks(project_id):
    """Генерирует action tasks для проекта (только Pro)."""
    user = g.current_user
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
    
    tasks_data, tokens_used = ai_service.generate_action_tasks(project)
    
    # Сохраняем задачи
    for task_data in tasks_data:
        task = ActionTask(
            project_id=project.id,
            user_id=user.id,
            title=task_data.get('title', ''),
            description=task_data.get('description', ''),
            category=task_data.get('category', 'content'),
            due_date=datetime.fromisoformat(task_data.get('due_date')).date() if task_data.get('due_date') else date.today(),
            ai_generated=True
        )
        db.session.add(task)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'Сгенерировано {len(tasks_data)} задач'})

@ai_bp.route('/tasks/<int:task_id>/update', methods=['POST'])
@login_required
def update_task(task_id):
    """Обновляет статус задачи."""
    user = g.current_user
    task = ActionTask.query.filter_by(id=task_id, user_id=user.id).first_or_404()
    
    data = request.get_json()
    status = data.get('status')
    
    if status in ['pending', 'in_progress', 'done', 'skipped']:
        task.status = status
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Invalid status'}), 400
