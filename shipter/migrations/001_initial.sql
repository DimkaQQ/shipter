-- ПОЛЬЗОВАТЕЛИ
CREATE TABLE users (
    id                    SERIAL PRIMARY KEY,
    email                 VARCHAR(255) UNIQUE NOT NULL,
    password_hash         VARCHAR(255),           -- NULL если Google OAuth
    name                  VARCHAR(255),
    google_id             VARCHAR(255) UNIQUE,    -- для Google OAuth
    avatar_url            VARCHAR(500),
    email_verified        BOOLEAN DEFAULT FALSE,
    email_verify_token    VARCHAR(255),
    tier                  VARCHAR(20) DEFAULT 'trial',  -- trial | starter | pro | expired
    trial_ends_at         TIMESTAMP,
    trial_reminder_sent   BOOLEAN DEFAULT FALSE,
    stripe_customer_id    VARCHAR(255),
    created_at            TIMESTAMP DEFAULT NOW(),
    last_seen             TIMESTAMP DEFAULT NOW()
);

-- ПРОЕКТЫ
CREATE TABLE projects (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name        VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    type        VARCHAR(50),    -- saas | bot | app | content | service | other
    audience    TEXT,
    problem     TEXT,
    website_url VARCHAR(500),
    status      VARCHAR(20) DEFAULT 'active',
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

-- AI ПЛАНЫ ДИСТРИБУЦИИ
CREATE TABLE distribution_plans (
    id                SERIAL PRIMARY KEY,
    project_id        INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    niche_analysis    TEXT,
    competitors       JSONB,         -- массив {name, pros, cons}
    monetization      JSONB,         -- массив {title, description, price, reasoning}
    distribution_steps JSONB,        -- массив {week, actions[]}
    quick_wins        JSONB,         -- массив {action, impact, effort, time}
    main_advice       TEXT,
    tokens_used       INTEGER,
    created_at        TIMESTAMP DEFAULT NOW()
);

-- СГЕНЕРИРОВАННЫЙ КОНТЕНТ
CREATE TABLE generated_content (
    id          SERIAL PRIMARY KEY,
    project_id  INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    user_id     INTEGER REFERENCES users(id),
    type        VARCHAR(50),   -- telegram_post | twitter_post | product_desc | landing_hero | email_sequence | cold_outreach
    content     TEXT NOT NULL,
    tokens_used INTEGER,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- ПОДПИСКИ STRIPE
CREATE TABLE subscriptions (
    id                      SERIAL PRIMARY KEY,
    user_id                 INTEGER REFERENCES users(id),
    stripe_subscription_id  VARCHAR(255) UNIQUE,
    stripe_price_id         VARCHAR(255),
    tier                    VARCHAR(20),    -- starter | pro
    status                  VARCHAR(20),    -- active | cancelled | past_due | unpaid
    current_period_start    TIMESTAMP,
    current_period_end      TIMESTAMP,
    cancel_at_period_end    BOOLEAN DEFAULT FALSE,
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);

-- ПОШАГОВЫЕ ЗАДАЧИ (для Pro плана — AI делает за пользователя)
CREATE TABLE action_tasks (
    id           SERIAL PRIMARY KEY,
    project_id   INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    user_id      INTEGER REFERENCES users(id),
    title        VARCHAR(500),
    description  TEXT,
    category     VARCHAR(50),   -- content | outreach | setup | analytics
    status       VARCHAR(20) DEFAULT 'pending',  -- pending | in_progress | done | skipped
    due_date     DATE,
    ai_generated BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMP DEFAULT NOW()
);

-- ИНДЕКСЫ
CREATE INDEX idx_projects_user     ON projects(user_id);
CREATE INDEX idx_plans_project     ON distribution_plans(project_id);
CREATE INDEX idx_content_project   ON generated_content(project_id);
CREATE INDEX idx_tasks_project     ON action_tasks(project_id, status);
CREATE INDEX idx_users_trial       ON users(trial_ends_at) WHERE tier = 'trial';
CREATE INDEX idx_users_stripe      ON users(stripe_customer_id);
