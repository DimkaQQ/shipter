from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from app.extensions import db
from app.models.project import Project
from app.models.integration import Integration
from app.models.generated_content import GeneratedContent
from app.models.publish_log import PublishLog
from app.middleware.auth import login_required, requires_pro
from app.services.publishing_service import (
    test_telegram_connection, publish_telegram, send_email_smtp
)

integrations_bp = Blueprint('integrations', __name__)


@integrations_bp.route('/<int:project_id>')
@login_required
@requires_pro
def list_integrations(project_id):
    user = g.current_user
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()
    integrations = project.integrations.order_by(Integration.created_at.desc()).all()
    return render_template('integrations/list.html', project=project, integrations=integrations)


@integrations_bp.route('/<int:project_id>/create', methods=['GET', 'POST'])
@login_required
@requires_pro
def create_integration(project_id):
    user = g.current_user
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()

    if request.method == 'POST':
        platform = request.form.get('platform')
        display_name = request.form.get('display_name', '').strip()

        if not display_name or platform not in ('telegram', 'email_smtp'):
            flash('Заполните все обязательные поля', 'error')
            return render_template('integrations/create.html', project=project)

        if platform == 'telegram':
            bot_token = request.form.get('bot_token', '').strip()
            chat_id = request.form.get('chat_id', '').strip()

            if not bot_token or not chat_id:
                flash('Укажите токен бота и chat_id канала', 'error')
                return render_template('integrations/create.html', project=project)

            ok, info = test_telegram_connection(bot_token)
            if not ok:
                flash(f'Не удалось подключить бота: {info}', 'error')
                return render_template('integrations/create.html', project=project)

            integration = Integration(project_id=project.id, platform='telegram', display_name=display_name)
            integration.set_config({'bot_token': bot_token, 'chat_id': chat_id})

        else:  # email_smtp
            smtp_host = request.form.get('smtp_host', '').strip()
            smtp_port = request.form.get('smtp_port', '587').strip()
            smtp_username = request.form.get('smtp_username', '').strip()
            smtp_password = request.form.get('smtp_password', '')
            use_tls = request.form.get('use_tls') == 'on'

            if not smtp_host or not smtp_username or not smtp_password:
                flash('Заполните все поля SMTP', 'error')
                return render_template('integrations/create.html', project=project)

            integration = Integration(project_id=project.id, platform='email_smtp', display_name=display_name)
            integration.set_config({
                'smtp_host': smtp_host,
                'smtp_port': smtp_port,
                'smtp_username': smtp_username,
                'smtp_password': smtp_password,
                'use_tls': use_tls,
            })

        db.session.add(integration)
        db.session.commit()

        flash('Интеграция подключена!', 'success')
        return redirect(url_for('integrations.list_integrations', project_id=project.id))

    return render_template('integrations/create.html', project=project)


@integrations_bp.route('/<int:integration_id>/delete', methods=['POST'])
@login_required
@requires_pro
def delete_integration(integration_id):
    user = g.current_user
    integration = Integration.query.join(Project).filter(
        Integration.id == integration_id, Project.user_id == user.id
    ).first_or_404()

    project_id = integration.project_id
    db.session.delete(integration)
    db.session.commit()

    flash('Интеграция удалена', 'success')
    return redirect(url_for('integrations.list_integrations', project_id=project_id))


@integrations_bp.route('/publish/<int:content_id>', methods=['POST'])
@login_required
@requires_pro
def publish_content(content_id):
    user = g.current_user
    content = GeneratedContent.query.filter_by(id=content_id, user_id=user.id).first_or_404()

    integration_id = request.form.get('integration_id', type=int)
    integration = Integration.query.filter_by(
        id=integration_id, project_id=content.project_id, is_active=True
    ).first()

    if not integration:
        flash('Интеграция не найдена', 'error')
        return redirect(url_for('projects.detail', project_id=content.project_id))

    if integration.platform == 'telegram':
        ok, error = publish_telegram(integration, content.content)
    else:
        recipients_raw = request.form.get('recipients', '')
        recipients = [r.strip() for r in recipients_raw.split(',') if r.strip()]
        if not recipients:
            flash('Укажите хотя бы один email получателя', 'error')
            return redirect(url_for('projects.detail', project_id=content.project_id))
        subject = f"{content.project.name} — {content.type}"
        ok, error = send_email_smtp(integration, subject, content.content, recipients)

    log = PublishLog(
        generated_content_id=content.id,
        integration_id=integration.id,
        status='success' if ok else 'failed',
        error_message=None if ok else error,
    )
    db.session.add(log)
    db.session.commit()

    if ok:
        flash(f'Опубликовано через {integration.display_name}!', 'success')
    else:
        flash(f'Ошибка публикации: {error}', 'error')

    return redirect(url_for('projects.detail', project_id=content.project_id))
