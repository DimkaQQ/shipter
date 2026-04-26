import hashlib
import json
import logging
from app.extensions import redis_client
from anthropic import Anthropic
from app.config import Config

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY) if Config.ANTHROPIC_API_KEY else None
    
    def _get_cache_key(self, project_id: int, prompt_type: str, description: str) -> str:
        raw = f"{project_id}:{prompt_type}:{description[:200]}"
        return f"ai:{hashlib.sha256(raw.encode()).hexdigest()}"
    
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
Отвечай ТОЛЬКО валидным JSON без markdown блоков. Язык — русский.

Проанализируй проект и верни JSON:
{{
  "niche_analysis": "3-5 предложений о нише, спросе, барьерах",
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
  "main_advice": "Самый важный совет в 2-3 предложения"
}}

Проект: {project.name}
Тип: {project.type}
Описание: {project.description}
Аудитория: {project.audience or 'Не указана'}
Проблема: {project.problem or 'Не указана'}
"""
            
            try:
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
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
                'cold_outreach': 'Напиши шаблон холодного сообщения для outreach в Telegram/email.'
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
                    model="claude-sonnet-4-20250514",
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
                    model="claude-sonnet-4-20250514",
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
            "main_advice": "Сфокусируйтесь на одной канале дистрибуции который даёт лучший ROI. Не распыляйтесь на всё сразу."
        }
    
    def _get_mock_content(self, content_type: str) -> str:
        """Mock контент для тестирования."""
        mocks = {
            'telegram_post': "🚀 Запускаем новый продукт!\n\nМы создали решение которое поможет вам сэкономить время и увеличить продажи.\n\n✅ Автоматизация процессов\n✅ Простая интеграция\n✅ Поддержка 24/7\n\nПопробуйте бесплатно 7 дней → ссылка\n\n#запуск #продукт #стартап",
            'twitter_post': "Только что запустили наш новый продукт! 🎉\n\nПервые 100 пользователей получают скидку 50%.\n\n#startup #launch #SaaS",
            'product_desc': "Устали тратить часы на рутинные задачи?\n\nНаш продукт автоматизирует ваши процессы и освобождает время для важного. Просто настройте один раз и забудьте о ручной работе.\n\nПопробуйте бесплатно уже сегодня!",
            'landing_hero': "Автоматизируйте свой бизнес за 15 минут\n\nБез кода. Без сложных настроек. Просто и эффективно.\n\nНачать бесплатно",
            'email_sequence': "Письмо 1 (Welcome):\nПривет! Спасибо за интерес к нашему продукту...\n\nПисьмо 2 (Day 3):\nКак проходит знакомство? Вот несколько советов...\n\nПисьмо 3 (Day 7):\nГотовы начать? Специальное предложение внутри...",
            'cold_outreach': "Привет! Вижу вы занимаетесь [тематика].\n\nМы помогли похожим компаниям увеличить [метрика] на X%.\n\nИнтересно узнать подробности?"
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
