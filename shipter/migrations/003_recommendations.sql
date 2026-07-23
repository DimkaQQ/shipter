-- РЕКОМЕНДАЦИИ СЕРВИСОВ И СТАРТАП-ХАБОВ (подбор через веб-поиск)
CREATE TABLE recommendations (
    id          SERIAL PRIMARY KEY,
    project_id  INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    services    JSONB,   -- массив {name, category, why_fits, url}
    hubs        JSONB,   -- массив {name, region, why_fits, url, offer_summary}
    tokens_used INTEGER,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_recommendations_project ON recommendations(project_id);
