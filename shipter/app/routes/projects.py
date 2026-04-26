from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from app.extensions import db
from app.models.project import Project
from app.middleware.auth import login_required, requires_active_subscription
from datetime import datetime, timezone

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
    content_items = project.generated_content.order_by(Project.generated_content.created_at.desc()).all()
    tasks = project.action_tasks.order_by(Project.action_tasks.due_date).all() if user.tier == 'pro' else []
    
    return render_template('projects/detail.html', 
                         project=project, 
                         plan=plan, 
                         content_items=content_items,
                         tasks=tasks)

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
