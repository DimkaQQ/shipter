from app.services.analytics_service import get_project_analytics_summary
from app.models.ad_creative import AdCreative
from app.models.ad_campaign_draft import AdCampaignDraft
from app.models.recommendation import Recommendation
from app.models.ad_guide import AdGuide


def _dt(value):
    return value.isoformat() if value else None


def build_user_export(user) -> dict:
    """Собирает все данные пользователя в JSON-совместимый словарь.
    Секреты (пароль, зашифрованные токены интеграций/рекламных кабинетов) не включаются."""
    data = {
        'account': {
            'email': user.email,
            'name': user.name,
            'tier': user.tier,
            'email_verified': user.email_verified,
            'created_at': _dt(user.created_at),
            'last_seen': _dt(user.last_seen),
        },
        'subscriptions': [
            {
                'tier': sub.tier,
                'status': sub.status,
                'current_period_start': _dt(sub.current_period_start),
                'current_period_end': _dt(sub.current_period_end),
                'cancel_at_period_end': sub.cancel_at_period_end,
                'created_at': _dt(sub.created_at),
            }
            for sub in user.subscriptions
        ],
        'projects': [],
    }

    for project in user.projects:
        project_data = {
            'name': project.name,
            'description': project.description,
            'type': project.type,
            'audience': project.audience,
            'problem': project.problem,
            'website_url': project.website_url,
            'status': project.status,
            'created_at': _dt(project.created_at),
        }

        if project.distribution_plan:
            plan = project.distribution_plan
            project_data['distribution_plan'] = {
                'niche_analysis': plan.niche_analysis,
                'competitors': plan.competitors,
                'monetization': plan.monetization,
                'distribution_steps': plan.distribution_steps,
                'quick_wins': plan.quick_wins,
                'main_advice': plan.main_advice,
                'sources': plan.sources,
                'created_at': _dt(plan.created_at),
            }

        recommendation = Recommendation.query.filter_by(project_id=project.id).order_by(Recommendation.created_at.desc()).first()
        if recommendation:
            project_data['recommendation'] = {
                'services': recommendation.services,
                'hubs': recommendation.hubs,
                'created_at': _dt(recommendation.created_at),
            }

        ad_guide = AdGuide.query.filter_by(project_id=project.id).order_by(AdGuide.created_at.desc()).first()
        if ad_guide:
            project_data['ad_guide'] = {
                'recommended_platforms': ad_guide.recommended_platforms,
                'budget_plan': ad_guide.budget_plan,
                'targeting': ad_guide.targeting,
                'campaign_structure': ad_guide.campaign_structure,
                'creative_tips': ad_guide.creative_tips,
                'sources': ad_guide.sources,
                'created_at': _dt(ad_guide.created_at),
            }

        project_data['generated_content'] = [
            {
                'type': c.type,
                'content': c.content,
                'created_at': _dt(c.created_at),
            }
            for c in project.generated_content
        ]

        project_data['action_tasks'] = [
            {
                'title': t.title,
                'description': t.description,
                'category': t.category,
                'status': t.status,
                'due_date': t.due_date.isoformat() if t.due_date else None,
                'created_at': _dt(t.created_at),
            }
            for t in project.action_tasks
        ]

        integrations = list(getattr(project, 'integrations', []))
        project_data['integrations'] = [
            {'platform': i.platform, 'display_name': i.display_name, 'is_active': i.is_active}
            for i in integrations
        ]

        subscribers = list(getattr(project, 'subscribers', []))
        project_data['subscribers'] = [
            {'email': s.email, 'source': s.source, 'subscribed': s.is_active, 'created_at': _dt(s.created_at)}
            for s in subscribers
        ]

        ad_creatives = AdCreative.query.filter_by(project_id=project.id).all()
        project_data['ad_creatives'] = [
            {'format': ac.format, 'headline': ac.headline, 'created_at': _dt(ac.created_at)}
            for ac in ad_creatives
        ]

        ad_drafts = AdCampaignDraft.query.filter_by(project_id=project.id).all()
        project_data['ad_campaign_drafts'] = [
            {
                'platform': d.platform,
                'name': d.name,
                'daily_budget': str(d.daily_budget) if d.daily_budget is not None else None,
                'country': d.country,
                'status': d.status,
                'created_at': _dt(d.created_at),
            }
            for d in ad_drafts
        ]

        summary = get_project_analytics_summary(project.id)
        project_data['analytics_summary'] = {
            **summary,
            'top_paths': [list(row) for row in summary['top_paths']],
            'top_referrers': [list(row) for row in summary['top_referrers']],
        }

        data['projects'].append(project_data)

    return data
