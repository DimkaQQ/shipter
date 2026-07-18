-- БАЗОВЫЕ РЕКЛАМНЫЕ КРЕАТИВЫ (SVG-баннеры, Starter/Pro)
CREATE TABLE ad_creatives (
    id          SERIAL PRIMARY KEY,
    project_id  INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    format      VARCHAR(20) NOT NULL,  -- square | landscape | story
    headline    VARCHAR(255),
    svg_markup  TEXT NOT NULL,
    tokens_used INTEGER,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ad_creatives_project ON ad_creatives(project_id);
