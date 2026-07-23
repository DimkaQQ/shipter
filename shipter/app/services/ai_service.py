import hashlib
import json
import logging
from app.extensions import redis_client
from anthropic import Anthropic
from app.config import Config
from app.services.svg_sanitizer import sanitize_svg
from app.services.analytics_service import get_project_analytics_summary_text
import httpx

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        if Config.ANTHROPIC_API_KEY:
            # Создаем httpx клиент без параметра proxies для совместимости
            http_client = httpx.Client()
            self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY, http_client=http_client)
        else:
            self.client = None
    
    def _get_cache_key(self, project_id: int, prompt_type: str, description: str) -> str:
        raw = f"{project_id}:{prompt_type}:{description[:200]}"
        return f"ai:{hashlib.sha256(raw.encode()).hexdigest()}"
    
    def _analytics_context(self, project_id: int) -> str:
        """Реальные данные встроенного счётчика — подмешиваются в промпт при повторном
        анализе, чтобы модель опиралась на факты о том, что уже сработало, а не только
        на описание проекта. Пусто, если по проекту ещё нет трафика."""
        summary = get_project_analytics_summary_text(project_id)
        if not summary:
            return ''
        return f"\nРеальные данные о трафике проекта (учти их при анализе): {summary}\n"

    def _final_text_block(self, response):
        """Возвращает текст последнего text-блока ответа.

        При веб-поиске (server-side tool) content — это чередование
        web_search_tool_result/text блоков, а не просто [text], поэтому
        нельзя полагаться на content[0].
        """
        for block in reversed(response.content):
            if block.type == 'text':
                return block.text
        return ''

    def _create_with_web_search(self, prompt: str, max_tokens: int, max_uses: int):
        """Вызывает Claude с веб-поиском, при pause_turn делает одно продолжение."""
        messages = [{"role": "user", "content": prompt}]
        response = self.client.messages.create(
            model="claude-opus-4-8",
            max_tokens=max_tokens,
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": max_uses}],
            messages=messages,
        )
        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            response = self.client.messages.create(
                model="claude-opus-4-8",
                max_tokens=max_tokens,
                tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": max_uses}],
                messages=messages,
            )
        return response

    def _cached_ai_call(self, key: str, ttl: int, fn):
        """Вызывает AI функцию с кешированием в Redis."""
        try:
            cached = redis_client.get(key)
            if cached:
                logger.info(f"Cache hit for key: {key}")
                return json.loads(cached), True
            
            result = fn()
            redis_client.setex(key, ttl, json.dumps(result, ensure_ascii=False))
            logger.info(f"Cache set for key: {key} with TTL: {ttl}")
            return result, False
        except Exception as e:
            logger.error(f"Redis error: {e}")
            # Fallback без кеширования
            return fn(), False
    
    def analyze_project(self, project) -> dict:
        """Анализирует проект и возвращает стратегию дистрибуции."""
        cache_key = self._get_cache_key(project.id, 'analyze', project.description)
        
        def do_analyze():
            if not self.client:
                return self._get_mock_analysis()

            prompt = f"""Ты — эксперт по запуску и дистрибуции цифровых продуктов.
У тебя есть инструмент веб-поиска — используй его, чтобы найти РЕАЛЬНЫХ, действующих сегодня
конкурентов, актуальные цены и текущие тренды в нише проекта. Не придумывай названия компаний,
цены или факты — если не нашёл через поиск, не включай в ответ.

Отвечай ТОЛЬКО валидным JSON без markdown блоков (это должен быть последний блок в ответе). Язык — русский.

Верни JSON:
{{
  "niche_analysis": "3-5 предложений о нише, спросе, барьерах — на основе найденного в поиске",
  "competitors": [
    {{"name": "...", "pros": ["...", "..."], "cons": ["...", "..."]}}
  ],
  "monetization": [
    {{"title": "...", "description": "...", "price": "...", "reasoning": "..."}}
  ],
  "distribution_steps": [
    {{"week": 1, "title": "...", "actions": ["...", "...", "..."]}},
    {{"week": 2, "title": "...", "actions": ["...", "...", "..."]}},
    {{"week": 3, "title": "...", "actions": ["...", "...", "..."]}},
    {{"week": 4, "title": "...", "actions": ["...", "...", "..."]}}
  ],
  "quick_wins": [
    {{"action": "...", "impact": "high|medium|low", "effort": "high|medium|low", "time": "..."}},
    {{"action": "...", "impact": "high|medium|low", "effort": "high|medium|low", "time": "..."}},
    {{"action": "...", "impact": "high|medium|low", "effort": "high|medium|low", "time": "..."}}
  ],
  "main_advice": "Самый важный совет в 2-3 предложения",
  "sources": [
    {{"title": "...", "url": "..."}}
  ]
}}

Проект: {project.name}
Тип: {project.type}
Описание: {project.description}
Аудитория: {project.audience or 'Не указана'}
Проблема: {project.problem or 'Не указана'}
{self._analytics_context(project.id)}"""

            try:
                response = self._create_with_web_search(prompt, max_tokens=8192, max_uses=5)
                content = self._final_text_block(response)
                # Очищаем от markdown если есть
                content = content.replace('```json', '').replace('```', '').strip()
                result = json.loads(content)
                tokens_used = response.usage.input_tokens + response.usage.output_tokens
                result['tokens_used'] = tokens_used
                return result
            except Exception as e:
                logger.error(f"AI analysis error: {e}")
                return self._get_mock_analysis()
        
        # TTL 24 часа для анализа
        return self._cached_ai_call(cache_key, 86400, do_analyze)
    
    def generate_content(self, project, content_type: str) -> str:
        """Генерирует контент указанного типа."""
        cache_key = self._get_cache_key(project.id, f'content_{content_type}', project.description)
        
        def do_generate():
            if not self.client:
                return self._get_mock_content(content_type)
            
            content_prompts = {
                'telegram_post': 'Напиши пост для Telegram канала (до 1000 символов) с эмодзи и CTA в конце.',
                'twitter_post': 'Напиши твит (до 280 символов) с хэштегами.',
                'product_desc': 'Напиши описание продукта в 3 абзаца: проблема → решение → CTA.',
                'landing_hero': 'Напиши заголовок, подзаголовок и текст CTA кнопки для лендинга.',
                'email_sequence': 'Напиши последовательность из 3 писем: welcome, day3 follow-up, day7 pitch.',
                'cold_outreach': 'Напиши шаблон холодного сообщения для outreach в Telegram/email.',
                'google_ads_search': (
                    'Напиши тексты для поисковой рекламы Google Ads (Responsive Search Ad): '
                    '5 заголовков (каждый до 30 символов, разные УТП) и 3 описания (каждое до 90 символов). '
                    'Оформи списком с пометками "Заголовок N:" и "Описание N:".'
                ),
                'meta_ads': (
                    'Напиши текст рекламного объявления для Meta Ads (Facebook/Instagram): '
                    'основной текст (2-3 варианта, до 125 символов каждый — короткий и цепляющий), '
                    'заголовок (до 40 символов), описание ссылки (до 30 символов).'
                ),
                'tiktok_ads': (
                    'Напиши сценарий для короткого рекламного видео TikTok Ads: '
                    'хук на первые 3 секунды, 3-4 ключевых кадра с текстом на экране, финальный CTA. '
                    'Плюс отдельно — текст подписи под видео с хэштегами.'
                ),
                'vk_ads': (
                    'Напиши тексты для ВКонтакте Реклама: заголовок (до 33 символов) '
                    'и 2 варианта текста объявления (до 220 символов каждый).'
                ),
                'yandex_direct': (
                    'Напиши тексты для Яндекс.Директ: заголовок 1 (до 56 символов), '
                    'заголовок 2 (до 30 символов), текст объявления (до 81 символа). '
                    'Дай 2 варианта на разные УТП.'
                ),
            }
            
            prompt = f"""Ты — копирайтер и маркетолог. 
Отвечай только готовым контентом без объяснений. Язык — русский.

{content_prompts.get(content_type, 'Напиши маркетинговый контент.')}

Проект: {project.name}
Описание: {project.description}
Аудитория: {project.audience or 'Не указана'}
"""
            
            try:
                response = self.client.messages.create(
                    model="claude-sonnet-5",
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text.strip()
                tokens_used = response.usage.input_tokens + response.usage.output_tokens
                return content, tokens_used
            except Exception as e:
                logger.error(f"AI content generation error: {e}")
                return self._get_mock_content(content_type), 0
        
        # TTL 1 час для контента
        return self._cached_ai_call(cache_key, 3600, do_generate)
    
    def generate_action_tasks(self, project) -> list:
        """Генерирует список задач на неделю (только для Pro)."""
        cache_key = self._get_cache_key(project.id, 'action_tasks', project.description)
        
        def do_generate():
            if not self.client:
                return self._get_mock_tasks()
            
            prompt = f"""Ты — проект-менеджер по запуску продуктов.
Верни ТОЛЬКО валидный JSON массив задач на следующие 7 дней.
Формат: [{{"title": "...", "description": "...", "category": "content|outreach|setup|analytics", "due_date": "YYYY-MM-DD", "estimated_minutes": 30}}]
Задачи должны быть конкретными и выполнимыми за 15-60 минут каждая.

Проект: {project.name}
Описание: {project.description}
"""
            
            try:
                response = self.client.messages.create(
                    model="claude-sonnet-5",
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
                content = content.replace('```json', '').replace('```', '').strip()
                tasks = json.loads(content)
                tokens_used = response.usage.input_tokens + response.usage.output_tokens
                return tasks, tokens_used
            except Exception as e:
                logger.error(f"AI task generation error: {e}")
                return self._get_mock_tasks(), 0
        
        # TTL 6 часов для задач
        return self._cached_ai_call(cache_key, 21600, do_generate)

    def recommend_services_and_hubs(self, project) -> dict:
        """Подбирает актуальные сервисы (хостинг/CRM/реклама) и стартап-хабы через веб-поиск."""
        cache_key = self._get_cache_key(project.id, 'recommend', project.description)

        def do_recommend():
            if not self.client:
                return self._get_mock_recommendations()

            prompt = f"""Ты — консультант по инфраструктуре и развитию стартапов.
У тебя есть инструмент веб-поиска — используй его, чтобы найти РЕАЛЬНО существующие и
действующие сегодня сервисы и стартап-хабы/акселераторы, подходящие именно этому проекту
(его нише, типу, региону, стадии). Для КАЖДОГО пункта обязательно укажи URL, найденный в
поиске. Если не уверен что сервис/хаб реально существует и активен — не включай его.

Отвечай ТОЛЬКО валидным JSON без markdown блоков (последний блок ответа). Язык — русский.

Верни JSON:
{{
  "services": [
    {{"name": "...", "category": "hosting|crm|ads|payments|analytics|no_code|email|other", "why_fits": "...", "url": "..."}}
  ],
  "hubs": [
    {{"name": "...", "region": "...", "why_fits": "...", "url": "...", "offer_summary": "что предлагает программа"}}
  ]
}}

Подбери 5-8 сервисов и 3-5 стартап-хабов/акселераторов.

Проект: {project.name}
Тип: {project.type}
Описание: {project.description}
Аудитория: {project.audience or 'Не указана'}
{self._analytics_context(project.id)}"""

            try:
                response = self._create_with_web_search(prompt, max_tokens=8192, max_uses=8)
                content = self._final_text_block(response)
                content = content.replace('```json', '').replace('```', '').strip()
                result = json.loads(content)
                tokens_used = response.usage.input_tokens + response.usage.output_tokens
                result['tokens_used'] = tokens_used
                return result
            except Exception as e:
                logger.error(f"AI recommendation error: {e}")
                return self._get_mock_recommendations()

        # TTL 7 дней — рекомендации меняются медленно, веб-поиск дорогой
        return self._cached_ai_call(cache_key, 604800, do_recommend)

    def _get_mock_recommendations(self) -> dict:
        """Mock рекомендации для тестирования без API ключа."""
        return {
            "services": [
                {"name": "Vercel", "category": "hosting", "why_fits": "Быстрый деплой для веб-приложений", "url": "https://vercel.com"},
                {"name": "Stripe", "category": "payments", "why_fits": "Приём платежей и подписок", "url": "https://stripe.com"}
            ],
            "hubs": [
                {"name": "Y Combinator", "region": "Global", "why_fits": "Ранняя стадия, широкий охват", "url": "https://www.ycombinator.com", "offer_summary": "Инвестиции + менторство"}
            ],
            "tokens_used": 0
        }

    def generate_ad_guide(self, project) -> dict:
        """Готовит гайд по запуску рекламы: площадки, бюджет, таргетинг, структура кампании."""
        cache_key = self._get_cache_key(project.id, 'ad_guide', project.description)

        def do_generate():
            if not self.client:
                return self._get_mock_ad_guide()

            prompt = f"""Ты — media buyer с опытом запуска рекламных кампаний для стартапов.
У тебя есть инструмент веб-поиска — используй его, чтобы учесть актуальные особенности
рекламных площадок (минимальные бюджеты, ограничения, что сейчас работает в нише проекта).
Не выдумывай цифры и правила площадок — опирайся на найденное в поиске.

Отвечай ТОЛЬКО валидным JSON без markdown блоков (последний блок ответа). Язык — русский.

Верни JSON:
{{
  "recommended_platforms": [
    {{"platform": "Google Ads | Meta Ads | TikTok Ads | VK Реклама | Яндекс.Директ | ...", "why": "почему подходит именно этому проекту", "budget_share_percent": 0-100}}
  ],
  "budget_plan": "рекомендация по стартовому бюджету и распределению между площадками, 3-5 предложений",
  "targeting": "кого таргетировать: аудитория, интересы, гео — 3-5 предложений",
  "campaign_structure": [
    {{"step": "Название этапа", "description": "что делать на этом этапе"}}
  ],
  "creative_tips": "какие форматы креативов и посылы использовать на старте, 3-5 предложений",
  "sources": [
    {{"title": "...", "url": "..."}}
  ]
}}

Распредели бюджет между 2-4 рекомендованными площадками (сумма budget_share_percent = 100).

Проект: {project.name}
Тип: {project.type}
Описание: {project.description}
Аудитория: {project.audience or 'Не указана'}
"""

            try:
                response = self._create_with_web_search(prompt, max_tokens=8192, max_uses=6)
                content = self._final_text_block(response)
                content = content.replace('```json', '').replace('```', '').strip()
                result = json.loads(content)
                tokens_used = response.usage.input_tokens + response.usage.output_tokens
                result['tokens_used'] = tokens_used
                return result
            except Exception as e:
                logger.error(f"AI ad guide error: {e}")
                return self._get_mock_ad_guide()

        # TTL 7 дней — специфика площадок меняется медленно, веб-поиск дорогой
        return self._cached_ai_call(cache_key, 604800, do_generate)

    def _get_mock_ad_guide(self) -> dict:
        """Mock гайд по рекламе для тестирования без API ключа."""
        return {
            "recommended_platforms": [
                {"platform": "Meta Ads", "why": "Широкий охват и точный таргетинг по интересам", "budget_share_percent": 60},
                {"platform": "Google Ads", "why": "Ловит спрос от людей, уже ищущих решение", "budget_share_percent": 40}
            ],
            "budget_plan": "Начните с $300-500 на 2 недели, разделив между площадками. Не увеличивайте бюджет, пока не увидите стабильный CPA.",
            "targeting": "Начните с широкой аудитории по интересам, близким к нише продукта, затем сузьте по данным первых кампаний.",
            "campaign_structure": [
                {"step": "Неделя 1: тест", "description": "Запустите 2-3 варианта креативов с минимальным бюджетом"},
                {"step": "Неделя 2: масштабирование", "description": "Увеличьте бюджет на связки с лучшим CPA"}
            ],
            "creative_tips": "Показывайте продукт в действии, используйте реальные цифры результата, тестируйте разные заголовки.",
            "sources": [],
            "tokens_used": 0
        }

    CREATIVE_FORMATS = {
        'square': {'width': 1080, 'height': 1080, 'label': 'Квадрат (Instagram/Facebook лента)'},
        'landscape': {'width': 1200, 'height': 628, 'label': 'Горизонтальный (Facebook/LinkedIn ссылка)'},
        'story': {'width': 1080, 'height': 1920, 'label': 'Сторис (Instagram/TikTok/Facebook)'},
    }

    def generate_ad_creative(self, project, format_key: str) -> dict:
        """Генерирует БАЗОВЫЙ рекламный баннер в виде SVG (без веб-поиска, без реальных фото).

        Это шаблонный баннер силами текстовой модели — фигуры, градиенты, текст.
        Не замена дизайнеру, годится как черновик/заглушка.
        """
        fmt = self.CREATIVE_FORMATS.get(format_key, self.CREATIVE_FORMATS['square'])
        cache_key = self._get_cache_key(project.id, f'creative_{format_key}', project.description)

        def do_generate():
            if not self.client:
                return self._get_mock_creative(fmt)

            prompt = f"""Ты — дизайнер простых рекламных баннеров. Сгенерируй ОДИН самодостаточный
SVG-баннер размером {fmt['width']}x{fmt['height']} пикселей.

Жёсткие правила:
- Ответ — ТОЛЬКО SVG-код, начинающийся с <svg и заканчивающийся </svg>. Без markdown, без пояснений.
- Только базовые фигуры (rect, circle, path, text, tspan) и градиенты (linearGradient/radialGradient). НИКАКИХ <script>, <image>, <foreignObject>, внешних ссылок и href.
- Только системные шрифты: font-family="Arial, Helvetica, sans-serif".
- Фон — сплошной цвет или простой linear gradient, отражающий характер продукта.
- Заголовок — короткий (до 6 слов), крупный, читаемый, помещается в баннер.
- Кнопка CTA — прямоугольник с текстом вроде "Попробовать бесплатно".
- Используй viewBox="0 0 {fmt['width']} {fmt['height']}" и width="{fmt['width']}" height="{fmt['height']}".

Проект: {project.name}
Описание: {project.description}
Аудитория: {project.audience or 'Не указана'}
"""

            try:
                response = self.client.messages.create(
                    model="claude-sonnet-5",
                    max_tokens=3072,
                    messages=[{"role": "user", "content": prompt}]
                )
                svg_raw = response.content[0].text.strip()
                svg_clean = sanitize_svg(svg_raw)
                tokens_used = response.usage.input_tokens + response.usage.output_tokens
                if not svg_clean:
                    logger.error("AI creative: could not parse/sanitize generated SVG, falling back to mock")
                    result = self._get_mock_creative(fmt)
                    result['tokens_used'] = tokens_used
                    return result
                return {'svg': svg_clean, 'headline': project.name, 'tokens_used': tokens_used}
            except Exception as e:
                logger.error(f"AI creative generation error: {e}")
                return self._get_mock_creative(fmt)

        # Не кешируем результат навсегда за тем же ключом, что и текст —
        # креативы регенерируются пользователем осознанно, поэтому короткий TTL
        return self._cached_ai_call(cache_key, 3600, do_generate)

    def _get_mock_creative(self, fmt: dict) -> dict:
        """Базовый безопасный SVG-баннер для тестирования без API ключа / как фолбэк."""
        w, h = fmt['width'], fmt['height']
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0%" stop-color="#6C5CE7"/><stop offset="100%" stop-color="#00B894"/>'
            f'</linearGradient></defs>'
            f'<rect width="{w}" height="{h}" fill="url(#bg)"/>'
            f'<text x="{w/2}" y="{h/2 - 20}" font-family="Arial, Helvetica, sans-serif" font-size="{int(w/16)}" '
            f'fill="#ffffff" text-anchor="middle" font-weight="bold">Ваш продукт</text>'
            f'<rect x="{w/2 - 130}" y="{h/2 + 20}" width="260" height="56" rx="10" fill="#ffffff"/>'
            f'<text x="{w/2}" y="{h/2 + 56}" font-family="Arial, Helvetica, sans-serif" font-size="20" '
            f'fill="#333333" text-anchor="middle">Попробовать бесплатно</text>'
            f'</svg>'
        )
        return {'svg': svg, 'headline': 'Ваш продукт', 'tokens_used': 0}

    def _get_mock_analysis(self) -> dict:
        """Mock анализ для тестирования без API ключа."""
        return {
            "niche_analysis": "Рынок цифровых продуктов растёт на 20% ежегодно. Ваша ниша перспективна но конкурентна.",
            "competitors": [
                {"name": "Competitor A", "pros": ["Большая аудитория", "Узнаваемый бренд"], "cons": ["Дорого", "Сложный интерфейс"]},
                {"name": "Competitor B", "pros": ["Низкая цена", "Простота"], "cons": ["Мало функций", "Нет поддержки"]}
            ],
            "monetization": [
                {"title": "Подписка", "description": "Ежемесячная подписка с доступом ко всем функциям", "price": "$29/мес", "reasoning": "Стабильный recurring revenue"},
                {"title": "Lifetime Deal", "description": "Единовременный платёж за пожизненный доступ", "price": "$199", "reasoning": "Быстрый cash flow на старте"}
            ],
            "distribution_steps": [
                {"week": 1, "title": "Подготовка", "actions": ["Создать соцсети", "Подготовить контент-план", "Настроить аналитику"]},
                {"week": 2, "title": "Первый запуск", "actions": ["Пост в Product Hunt", "Рассылка по базе", "Посты в Telegram"]},
                {"week": 3, "title": "Масштабирование", "actions": ["Реклама в каналах", "Collab с блогерами", "Email серия"]},
                {"week": 4, "title": "Оптимизация", "actions": ["Анализ метрик", "A/B тесты", "Сбор фидбека"]}
            ],
            "quick_wins": [
                {"action": "Пост в Product Hunt", "impact": "high", "effort": "medium", "time": "2 часа"},
                {"action": "Рассылка по LinkedIn", "impact": "medium", "effort": "low", "time": "30 минут"},
                {"action": "Гостевой пост", "impact": "medium", "effort": "high", "time": "4 часа"}
            ],
            "main_advice": "Сфокусируйтесь на одной канале дистрибуции который даёт лучший ROI. Не распыляйтесь на всё сразу.",
            "sources": []
        }
    
    def _get_mock_content(self, content_type: str) -> str:
        """Mock контент для тестирования."""
        mocks = {
            'telegram_post': "🚀 Запускаем новый продукт!\n\nМы создали решение которое поможет вам сэкономить время и увеличить продажи.\n\n✅ Автоматизация процессов\n✅ Простая интеграция\n✅ Поддержка 24/7\n\nПопробуйте бесплатно 7 дней → ссылка\n\n#запуск #продукт #стартап",
            'twitter_post': "Только что запустили наш новый продукт! 🎉\n\nПервые 100 пользователей получают скидку 50%.\n\n#startup #launch #SaaS",
            'product_desc': "Устали тратить часы на рутинные задачи?\n\nНаш продукт автоматизирует ваши процессы и освобождает время для важного. Просто настройте один раз и забудьте о ручной работе.\n\nПопробуйте бесплатно уже сегодня!",
            'landing_hero': "Автоматизируйте свой бизнес за 15 минут\n\nБез кода. Без сложных настроек. Просто и эффективно.\n\nНачать бесплатно",
            'email_sequence': "Письмо 1 (Welcome):\nПривет! Спасибо за интерес к нашему продукту...\n\nПисьмо 2 (Day 3):\nКак проходит знакомство? Вот несколько советов...\n\nПисьмо 3 (Day 7):\nГотовы начать? Специальное предложение внутри...",
            'cold_outreach': "Привет! Вижу вы занимаетесь [тематика].\n\nМы помогли похожим компаниям увеличить [метрика] на X%.\n\nИнтересно узнать подробности?",
            'google_ads_search': "Заголовок 1: Автоматизация за 15 минут\nЗаголовок 2: Без кода и настройки\nЗаголовок 3: Попробуйте бесплатно\nЗаголовок 4: Экономьте часы в неделю\nЗаголовок 5: Начните сегодня\n\nОписание 1: Автоматизируйте рутину и освободите время для важного. Бесплатный старт.\nОписание 2: Простая интеграция, поддержка 24/7. Попробуйте без риска.\nОписание 3: Более 100 команд уже автоматизировали процессы с нами.",
            'meta_ads': "Основной текст 1: Устали тратить часы на рутину? Автоматизируйте её за 15 минут — без кода.\nОсновной текст 2: 100+ команд уже сэкономили время с нашим продуктом. Ваша очередь.\n\nЗаголовок: Автоматизация за 15 минут\nОписание: Без кода и сложных настроек",
            'tiktok_ads': "Хук (0-3 сек): «Тратишь по 3 часа в день на рутину?»\nКадр 1: показать проблему (хаос с таблицами/задачами)\nКадр 2: экран продукта — настройка за пару кликов\nКадр 3: результат — довольный пользователь, счётчик сэкономленного времени\nCTA: «Попробуй бесплатно — ссылка в шапке»\n\nПодпись: Автоматизация рутины за 15 минут 🚀 #продуктивность #автоматизация #стартап",
            'vk_ads': "Заголовок: Автоматизация за 15 минут\n\nВариант 1: Устали от рутины? Настройте автоматизацию за 15 минут без кода. Первые 7 дней бесплатно.\nВариант 2: Более 100 команд уже сэкономили время с нашим продуктом. Попробуйте бесплатно уже сегодня.",
            'yandex_direct': "Вариант 1:\nЗаголовок 1: Автоматизация без кода\nЗаголовок 2: Бесплатно 7 дней\nТекст: Настройте за 15 минут и экономьте часы каждую неделю\n\nВариант 2:\nЗаголовок 1: Экономьте время на рутине\nЗаголовок 2: Простая настройка\nТекст: Автоматизация процессов для вашей команды. Попробуйте бесплатно",
        }
        return mocks.get(content_type, "Контент будет сгенерирован AI...")
    
    def _get_mock_tasks(self) -> list:
        """Mock задачи для тестирования."""
        from datetime import date, timedelta
        today = date.today()
        return [
            {"title": "Создать аккаунты в соцсетях", "description": "Зарегистрироваться в Twitter, LinkedIn, Telegram", "category": "setup", "due_date": (today + timedelta(days=1)).isoformat(), "estimated_minutes": 30},
            {"title": "Написать первый пост", "description": "Подготовить анонс продукта для всех каналов", "category": "content", "due_date": (today + timedelta(days=2)).isoformat(), "estimated_minutes": 45},
            {"title": "Найти 10 потенциальных клиентов", "description": "Составить список для cold outreach", "category": "outreach", "due_date": (today + timedelta(days=3)).isoformat(), "estimated_minutes": 60},
            {"title": "Настроить Google Analytics", "description": "Установить трекеры на лендинг", "category": "analytics", "due_date": (today + timedelta(days=4)).isoformat(), "estimated_minutes": 30}
        ]

ai_service = AIService()
