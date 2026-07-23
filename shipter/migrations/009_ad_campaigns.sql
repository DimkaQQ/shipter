-- ПОДКЛЮЧЕНИЕ РЕКЛАМНОГО КАБИНЕТА (Meta Ads, Pro)
CREATE TABLE ad_account_connections (
    id                SERIAL PRIMARY KEY,
    project_id        INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    platform          VARCHAR(20) NOT NULL DEFAULT 'meta',
    encrypted_config  TEXT NOT NULL,   -- access_token, ad_account_id, page_id (Fernet)
    created_at        TIMESTAMP DEFAULT NOW()
);

-- ЧЕРНОВИКИ РЕКЛАМНЫХ КАМПАНИЙ (Campaign+AdSet в статусе PAUSED, без автозапуска)
CREATE TABLE ad_campaign_drafts (
    id                     SERIAL PRIMARY KEY,
    project_id             INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    platform               VARCHAR(20) NOT NULL DEFAULT 'meta',
    name                   VARCHAR(255) NOT NULL,
    daily_budget           NUMERIC(10, 2),
    country                VARCHAR(2),
    external_campaign_id   VARCHAR(64),
    external_adset_id      VARCHAR(64),
    status                 VARCHAR(20) DEFAULT 'draft_created',  -- draft_created | failed
    error_message          TEXT,
    ads_manager_url        VARCHAR(500),
    created_at             TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ad_account_connections_project ON ad_account_connections(project_id);
CREATE INDEX idx_ad_campaign_drafts_project ON ad_campaign_drafts(project_id);
