from datetime import datetime, timezone, timedelta
from sqlalchemy import func
from app.models.analytics_event import AnalyticsEvent


def get_project_analytics_summary(project_id: int) -> dict:
    """Агрегированная статистика встраиваемого счётчика — единая точка правды
    для вкладки 'Аналитика' и для обратной связи в AI-промптах."""
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


def get_project_analytics_summary_text(project_id: int) -> str:
    """Короткий абзац для подмешивания в AI-промпт при повторном анализе.
    Возвращает '', если данных ещё нет — чтобы не засорять промпт пустой секцией."""
    stats = get_project_analytics_summary(project_id)

    if stats['total_pageviews'] == 0:
        return ''

    lines = [
        f"За последние 30 дней сайт проекта посетили {stats['pageviews_30d']} раз "
        f"(примерно {stats['unique_visitors_30d']} уникальных посетителей)."
    ]

    if stats['top_referrers']:
        top = ', '.join(f"{ref} ({cnt})" for ref, cnt in stats['top_referrers'][:3])
        lines.append(f"Основные источники трафика: {top}.")

    if stats['top_paths']:
        top = ', '.join(f"{path or '/'} ({cnt})" for path, cnt in stats['top_paths'][:3])
        lines.append(f"Популярные страницы: {top}.")

    return ' '.join(lines)
