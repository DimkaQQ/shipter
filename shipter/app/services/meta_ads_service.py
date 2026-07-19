import json
import logging
import requests
from app.config import Config

logger = logging.getLogger(__name__)

GRAPH_API_TIMEOUT = 15


def _graph_base() -> str:
    return f"https://graph.facebook.com/{Config.META_API_VERSION}"


def exchange_long_lived_token(short_token: str) -> tuple[bool, str]:
    """Обменивает короткоживущий OAuth-токен на долгоживущий (~60 дней)."""
    try:
        resp = requests.get(
            f"{_graph_base()}/oauth/access_token",
            params={
                'grant_type': 'fb_exchange_token',
                'client_id': Config.META_APP_ID,
                'client_secret': Config.META_APP_SECRET,
                'fb_exchange_token': short_token,
            },
            timeout=GRAPH_API_TIMEOUT,
        )
        data = resp.json()
        if resp.status_code == 200 and 'access_token' in data:
            return True, data['access_token']
        return False, data.get('error', {}).get('message', 'Не удалось обменять токен')
    except requests.RequestException as e:
        logger.error(f"Meta token exchange error: {e}")
        return False, 'Не удалось подключиться к Meta API'


def list_ad_accounts(access_token: str):
    """Возвращает (успех, список рекламных кабинетов пользователя или текст ошибки)."""
    try:
        resp = requests.get(
            f"{_graph_base()}/me/adaccounts",
            params={'access_token': access_token, 'fields': 'id,name,account_status'},
            timeout=GRAPH_API_TIMEOUT,
        )
        data = resp.json()
        if resp.status_code == 200:
            return True, data.get('data', [])
        return False, data.get('error', {}).get('message', 'Не удалось получить рекламные кабинеты')
    except requests.RequestException as e:
        logger.error(f"Meta list ad accounts error: {e}")
        return False, 'Не удалось подключиться к Meta API'


def create_draft_campaign(connection, name: str, daily_budget_cents: int, country: str):
    """Создаёт Campaign + AdSet в статусе PAUSED — черновик без автозапуска и без реального
    расхода бюджета. Ad/Creative намеренно не создаётся (нужна была бы серверная растеризация
    SVG в PNG для загрузки изображения — вне текущего объёма). Возвращает (успех, dict-результат)."""
    config = connection.get_config()
    access_token = config.get('access_token')
    ad_account_id = config.get('ad_account_id')

    try:
        campaign_resp = requests.post(
            f"{_graph_base()}/act_{ad_account_id}/campaigns",
            data={
                'name': name,
                'objective': 'OUTCOME_TRAFFIC',
                'status': 'PAUSED',
                'special_ad_categories': '[]',
                'access_token': access_token,
            },
            timeout=GRAPH_API_TIMEOUT,
        )
        campaign_data = campaign_resp.json()
        if campaign_resp.status_code != 200 or 'id' not in campaign_data:
            error = campaign_data.get('error', {}).get('message', 'Не удалось создать кампанию')
            return False, {'error': error}

        campaign_id = campaign_data['id']

        adset_resp = requests.post(
            f"{_graph_base()}/act_{ad_account_id}/adsets",
            data={
                'name': f"{name} — AdSet",
                'campaign_id': campaign_id,
                'daily_budget': daily_budget_cents,
                'billing_event': 'IMPRESSIONS',
                'optimization_goal': 'LINK_CLICKS',
                'bid_strategy': 'LOWEST_COST_WITHOUT_CAP',
                'status': 'PAUSED',
                'targeting': json.dumps({
                    'age_min': 18,
                    'age_max': 65,
                    'geo_locations': {'countries': [country]},
                }),
                'access_token': access_token,
            },
            timeout=GRAPH_API_TIMEOUT,
        )
        adset_data = adset_resp.json()
        if adset_resp.status_code != 200 or 'id' not in adset_data:
            error = adset_data.get('error', {}).get('message', 'Не удалось создать группу объявлений')
            return False, {'error': error, 'campaign_id': campaign_id}

        return True, {
            'campaign_id': campaign_id,
            'adset_id': adset_data['id'],
            'ads_manager_url': f"https://www.facebook.com/adsmanager/manage/campaigns?act={ad_account_id}",
        }
    except requests.RequestException as e:
        logger.error(f"Meta campaign creation error: {e}")
        return False, {'error': 'Не удалось подключиться к Meta API'}
