-- ПОДПИСЧИКИ (CRM для email-рассылок)
CREATE TABLE subscribers (
    id                  SERIAL PRIMARY KEY,
    project_id          INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    email               VARCHAR(255) NOT NULL,
    source              VARCHAR(20) DEFAULT 'manual',  -- manual | signup_form
    unsubscribe_token   VARCHAR(64) UNIQUE NOT NULL,
    unsubscribed_at     TIMESTAMP,
    created_at          TIMESTAMP DEFAULT NOW(),
    UNIQUE (project_id, email)
);

CREATE INDEX idx_subscribers_project ON subscribers(project_id);
