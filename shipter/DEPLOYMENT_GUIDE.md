# 🔐 DOMAIN CONNECTION GUIDE — Shipter

## Полное руководство по подключению домена shipter.com

---

## 📋 Шаг 1: Подготовка DNS записей

### 1.1 Зарегистрируйте домен (если ещё не сделали)
- Купите домен `shipter.com` у регистратора (Namecheap, GoDaddy, Cloudflare и т.д.)
- Рекомендуется использовать **Cloudflare** для управления DNS (бесплатно + защита от DDoS)

### 1.2 Настройте DNS записи

#### Вариант A: Прямое подключение к серверу
```
Тип записи: A
Имя: @
Значение: <IP-адрес вашего сервера>
TTL: Auto

Тип записи: CNAME
Имя: www
Значение: shipter.com
TTL: Auto
```

#### Вариант B: Через Cloudflare (рекомендуется)
1. Добавьте сайт в Cloudflare
2. Измените nameservers на те, что предоставит Cloudflare
3. Cloudflare автоматически создаст DNS записи
4. Включите SSL/TLS режим "Full" или "Full (strict)"

---

## 🖥️ Шаг 2: Настройка сервера

### 2.1 Установите Nginx (если ещё не установлен)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx -y

# macOS (для локальной разработки)
brew install nginx
```

### 2.2 Настройте Nginx

Скопируйте конфигурацию из файла `nginx.conf` в директорию Nginx:

```bash
# Linux
sudo cp /path/to/shipter/nginx.conf /etc/nginx/sites-available/shipter.com
sudo ln -s /etc/nginx/sites-available/shipter.com /etc/nginx/sites-enabled/

# Проверка конфигурации
sudo nginx -t

# Перезапуск Nginx
sudo systemctl restart nginx
```

### 2.3 Конфигурация Nginx (nginx.conf уже в проекте)

Основные моменты:
- Проксирование на порт 5000 (Flask)
- Поддержка WebSocket (если нужно)
- Rate limiting для защиты
- Сжатие gzip
- HTTPS редирект

---

## 🔒 Шаг 3: Установка SSL сертификата

### 3.1 Бесплатный SSL через Let's Encrypt

```bash
# Установите Certbot
sudo apt install certbot python3-certbot-nginx -y

# Получите сертификат
sudo certbot --nginx -d shipter.com -d www.shipter.com

# Автоматическое продление (добавьте в cron)
sudo certbot renew --dry-run
```

### 3.2 Обновите конфиг Nginx для HTTPS

Certbot автоматически обновит конфигурацию Nginx.

Проверьте:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🚀 Шаг 4: Запуск приложения в production

### 4.1 Используйте Gunicorn вместо Flask dev server

```bash
# Установите Gunicorn (уже в requirements.txt)
pip install gunicorn

# Запустите через Gunicorn
gunicorn --config gunicorn.conf.py run:app
```

### 4.2 Настройте systemd service (Linux)

Файл `shipter.service` уже создан в проекте:

```bash
# Скопируйте файл службы
sudo cp /path/to/shipter/shipter.service /etc/systemd/system/

# Обновите пути в файле службы
sudo nano /etc/systemd/system/shipter.service

# Активируйте службу
sudo systemctl daemon-reload
sudo systemctl enable shipter
sudo systemctl start shipter

# Проверка статуса
sudo systemctl status shipter
```

### 4.2.1 Планировщик фоновых задач (trial reminders)

Планировщик (напоминания об истечении триала) запускается **отдельным процессом**,
а не внутри Gunicorn-воркеров — иначе задачи и письма дублировались бы по числу воркеров.

```bash
# Скопируйте файл службы
sudo cp /path/to/shipter/shipter-scheduler.service /etc/systemd/system/

# Обновите пути в файле службы
sudo nano /etc/systemd/system/shipter-scheduler.service

# Активируйте службу
sudo systemctl daemon-reload
sudo systemctl enable shipter-scheduler
sudo systemctl start shipter-scheduler

# Проверка статуса
sudo systemctl status shipter-scheduler
```

### 4.3 Для macOS (локальная разработка)

Используйте launchd или просто запускайте через:
```bash
gunicorn --bind 0.0.0.0:5000 run:app
```

---

## 🌐 Шаг 5: Финальная проверка

### 5.1 Проверьте доступность сайта

```bash
# Проверка DNS
dig shipter.com
nslookup shipter.com

# Проверка HTTPS
curl -I https://shipter.com

# Проверка редиректа HTTP → HTTPS
curl -I http://shipter.com
```

### 5.2 Онлайн инструменты

- [SSL Labs Test](https://www.ssllabs.com/ssltest/) — проверка SSL
- [GTmetrix](https://gtmetrix.com/) — производительность
- [Down For Everyone Or Just Me](https://downforeveryoneorjustme.com/) — доступность

---

## 🔧 Дополнительные настройки

### ENCRYPTION_KEY (для интеграций Telegram/SMTP на Pro)

Токены и пароли, которые пользователи вводят при подключении интеграций, хранятся в БД
зашифрованными (Fernet). Сгенерируйте ключ один раз и никогда не меняйте его после того,
как в базе появятся интеграции (иначе расшифровка существующих записей сломается):

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Положите результат в `.env` как `ENCRYPTION_KEY=...`.

### META_APP_ID / META_APP_SECRET (черновики кампаний Meta Ads, Pro)

Фича создаёт черновики рекламных кампаний (Campaign + AdSet в статусе «на паузе», без
автозапуска и без расхода бюджета) через Graph API от имени пользователя. Чтобы это
реально заработало для всех пользователей, а не только для вас как разработчика:

1. Зарегистрируйте приложение на [developers.facebook.com](https://developers.facebook.com/apps/) —
   добавьте продукт **Marketing API**, настройте OAuth redirect URI:
   `https://ваш-домен/meta-ads/callback`.
2. Пройдите **App Review** на permission `ads_management` (и `pages_show_list`,
   `business_management`). Без этого OAuth будет работать только для админов/тестеров
   вашего приложения — процесс модерации у Meta занимает от нескольких дней до недель.
3. Положите `META_APP_ID` / `META_APP_SECRET` из настроек приложения в `.env`.

Пока `META_APP_ID`/`META_APP_SECRET` не заданы — раздел «Черновик кампании в Meta Ads»
в интерфейсе будет отдавать понятную ошибку вместо падения приложения.

### Переменные окружения для production

Создайте файл `.env` на сервере:

```bash
# Flask
SECRET_KEY=<очень_секретный_ключ>
FLASK_ENV=production
DEBUG=False
APP_URL=https://shipter.com

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/shipter_db

# Redis
REDIS_URL=redis://localhost:6379/0

# AI
ANTHROPIC_API_KEY=sk-ant-...

# Stripe
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_STARTER=price_...
STRIPE_PRICE_PRO=price_...

# Google OAuth
GOOGLE_CLIENT_ID=....apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=...

# Email (SMTP)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=hello@shipter.com
MAIL_PASSWORD=...

# Trial
TRIAL_DAYS=3
```

⚠️ **Никогда не коммитьте `.env` файл в Git!**

---

## 🛡️ Безопасность

### Рекомендации по безопасности:

1. **Firewall**
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw allow 22/tcp
   sudo ufw enable
   ```

2. **Rate Limiting** (уже в nginx.conf)
   - Ограничение запросов к API
   - Защита от brute force

3. **HTTPS Only**
   - Все запросы перенаправляются на HTTPS
   - HSTS заголовок

4. **Secure Cookies**
   - HttpOnly флаг
   - Secure флаг (только HTTPS)
   - SameSite=Strict

5. **SQL Injection Protection**
   - SQLAlchemy ORM с параметризованными запросами

6. **XSS Protection**
   - Flask auto-escaping
   - Content-Security-Policy заголовки

7. **CSRF Protection**
   - Flask sessions с SECRET_KEY

8. **Password Hashing**
   - bcrypt с salt

---

## 📊 Мониторинг

### Логи приложения

```bash
# Просмотр логов systemd
sudo journalctl -u shipter -f

# Логи Nginx
sudo tail -f /var/log/nginx/shipter.com.error.log
sudo tail -f /var/log/nginx/shipter.com.access.log
```

### Мониторинг ресурсов

```bash
# Установите htop
sudo apt install htop

# Мониторинг в реальном времени
htop

# Использование памяти
free -h

# Использование диска
df -h
```

---

## 🔄 Обновление приложения

```bash
# Зайдите на сервер
cd /path/to/shipter

# Обновите код
git pull origin main

# Установите зависимости
pip install -r requirements.txt

# Перезапустите приложение
sudo systemctl restart shipter

# Или перезагрузите Nginx если меняли конфиг
sudo systemctl reload nginx
```

---

## 🆘 Troubleshooting

### Проблема: Сайт не открывается

1. Проверьте DNS: `dig shipter.com`
2. Проверьте Firewall: `sudo ufw status`
3. Проверьте Nginx: `sudo systemctl status nginx`
4. Проверьте приложение: `sudo systemctl status shipter`
5. Проверьте логи: `sudo journalctl -u shipter -n 50`

### Проблема: SSL не работает

1. Проверьте сертификат: `sudo certbot certificates`
2. Продлите сертификат: `sudo certbot renew`
3. Проверьте конфиг Nginx: `sudo nginx -t`

### Проблема: Приложение падает

1. Проверьте переменные окружения
2. Проверьте подключение к БД
3. Проверьте логи: `sudo journalctl -u shipter -f`

---

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи
2. Погуглите ошибку
3. Обратитесь в поддержку хостинга
4. Проверьте документацию Flask/Nginx/Certbot

---

**Удачи с запуском Shipter! 🚀**
