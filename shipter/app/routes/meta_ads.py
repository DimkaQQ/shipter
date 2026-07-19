from decimal import Decimal, InvalidOperation
from flask import Blueprint, redirect, url_for, flash, g, session, request, render_template
from app.extensions import db, oauth
from app.models.project import Project
from app.models.ad_account_connection import AdAccountConnection
from app.models.ad_campaign_draft import AdCampaignDraft
from app.middleware.auth import login_required, requires_pro
from app.services import meta_ads_service

meta_ads_bp = Blueprint('meta_ads', __name__)


@meta_ads_bp.route('/connect/<int:project_id>')
@login_required
@requires_pro
def connect(project_id):
    user = g.current_user
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()

    if not hasattr(oauth, 'meta'):
        flash('Подключение Meta Ads не настроено на сервере', 'error')
        return redirect(url_for('projects.detail', project_id=project.id))

    session['meta_oauth_project_id'] = project.id
    redirect_uri = url_for('meta_ads.callback', _external=True)
    return oauth.meta.authorize_redirect(redirect_uri)


@meta_ads_bp.route('/callback')
@login_required
def callback():
    project_id = session.pop('meta_oauth_project_id', None)
    if not project_id:
        flash('Сессия подключения истекла, попробуйте снова', 'error')
        return redirect(url_for('projects.list_projects'))

    user = g.current_user
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()

    if not hasattr(oauth, 'meta'):
        flash('Подключение Meta Ads не настроено на сервере', 'error')
        return redirect(url_for('projects.detail', project_id=project.id))

    try:
        token = oauth.meta.authorize_access_token()
    except Exception:
        flash('Ошибка авторизации через Meta', 'error')
        return redirect(url_for('projects.detail', project_id=project.id))

    short_token = token.get('access_token') if token else None
    if not short_token:
        flash('Не удалось получить токен доступа Meta', 'error')
        return redirect(url_for('projects.detail', project_id=project.id))

    ok, exchanged = meta_ads_service.exchange_long_lived_token(short_token)
    access_token = exchanged if ok else short_token

    ok, accounts = meta_ads_service.list_ad_accounts(access_token)
    if not ok:
        flash(f'Не удалось получить рекламные кабинеты: {accounts}', 'error')
        return redirect(url_for('projects.detail', project_id=project.id))

    if not accounts:
        flash('У вашего Meta-аккаунта нет доступных рекламных кабинетов', 'error')
        return redirect(url_for('projects.detail', project_id=project.id))

    if len(accounts) == 1:
        _save_connection(project.id, access_token, accounts[0]['id'])
        flash('Рекламный кабинет Meta подключён!', 'success')
        return redirect(url_for('projects.detail', project_id=project.id))

    # Несколько кабинетов у аккаунта — просим выбрать
    session['meta_pending_token'] = access_token
    session['meta_pending_project_id'] = project.id
    return render_template('ai/meta_account_picker.html', project=project, accounts=accounts)


@meta_ads_bp.route('/choose-account', methods=['POST'])
@login_required
@requires_pro
def choose_account():
    access_token = session.pop('meta_pending_token', None)
    project_id = session.pop('meta_pending_project_id', None)
    ad_account_id = request.form.get('ad_account_id')

    if not access_token or not project_id or not ad_account_id:
        flash('Сессия выбора кабинета истекла, попробуйте снова', 'error')
        return redirect(url_for('projects.list_projects'))

    user = g.current_user
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()

    _save_connection(project.id, access_token, ad_account_id)
    flash('Рекламный кабинет Meta подключён!', 'success')
    return redirect(url_for('projects.detail', project_id=project.id))


def _save_connection(project_id: int, access_token: str, ad_account_id: str):
    connection = AdAccountConnection(project_id=project_id, platform='meta')
    connection.set_config({
        'access_token': access_token,
        'ad_account_id': ad_account_id.replace('act_', ''),
    })
    db.session.add(connection)
    db.session.commit()


@meta_ads_bp.route('/campaign/<int:project_id>', methods=['GET', 'POST'])
@login_required
@requires_pro
def create_campaign(project_id):
    """Создаёт черновик кампании (Campaign + AdSet, статус PAUSED — без автозапуска)."""
    user = g.current_user
    project = Project.query.filter_by(id=project_id, user_id=user.id).first_or_404()

    connection = AdAccountConnection.query.filter_by(
        project_id=project.id, platform='meta'
    ).order_by(AdAccountConnection.created_at.desc()).first()

    if not connection:
        flash('Сначала подключите рекламный кабинет Meta', 'warning')
        return redirect(url_for('projects.detail', project_id=project.id))

    if request.method == 'POST':
        name = request.form.get('name', '').strip() or project.name
        country = (request.form.get('country', 'US').strip() or 'US').upper()[:2]

        try:
            daily_budget = Decimal(request.form.get('daily_budget', '0'))
        except InvalidOperation:
            daily_budget = Decimal('0')

        if daily_budget <= 0:
            flash('Укажите дневной бюджет больше нуля', 'error')
            return render_template('ai/meta_campaign.html', project=project)

        daily_budget_cents = int(daily_budget * 100)
        ok, result = meta_ads_service.create_draft_campaign(connection, name, daily_budget_cents, country)

        draft = AdCampaignDraft(
            project_id=project.id,
            platform='meta',
            name=name,
            daily_budget=daily_budget,
            country=country,
            status='draft_created' if ok else 'failed',
            external_campaign_id=result.get('campaign_id') if ok else None,
            external_adset_id=result.get('adset_id') if ok else None,
            ads_manager_url=result.get('ads_manager_url') if ok else None,
            error_message=None if ok else result.get('error'),
        )
        db.session.add(draft)
        db.session.commit()

        if ok:
            flash('Черновик кампании создан в статусе "на паузе" — донастройте и запустите в Ads Manager', 'success')
        else:
            flash(f'Не удалось создать черновик: {result.get("error")}', 'error')

        return redirect(url_for('projects.detail', project_id=project.id))

    return render_template('ai/meta_campaign.html', project=project)
