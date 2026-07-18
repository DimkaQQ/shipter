-- АНАЛИТИКА ПО ВСТРАИВАЕМОМУ СЧЁТЧИКУ
CREATE TABLE analytics_events (
    id            SERIAL PRIMARY KEY,
    project_id    INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    event_type    VARCHAR(20) NOT NULL DEFAULT 'pageview',
    path          VARCHAR(500),
    referrer      VARCHAR(500),
    visitor_hash  VARCHAR(64),
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_analytics_project_date ON analytics_events(project_id, created_at);
