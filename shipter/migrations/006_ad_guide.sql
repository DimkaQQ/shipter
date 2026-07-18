-- ГАЙД ПО ЗАПУСКУ РЕКЛАМЫ
CREATE TABLE ad_guides (
    id                      SERIAL PRIMARY KEY,
    project_id              INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    recommended_platforms   JSONB,   -- массив {platform, why, budget_share_percent}
    budget_plan             TEXT,
    targeting               TEXT,
    campaign_structure      JSONB,   -- массив {step, description}
    creative_tips           TEXT,
    sources                 JSONB,   -- массив {title, url}
    tokens_used             INTEGER,
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ad_guides_project ON ad_guides(project_id);
