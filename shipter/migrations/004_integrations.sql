-- ИНТЕГРАЦИИ ДЛЯ РЕАЛЬНОЙ АВТО-ПУБЛИКАЦИИ (Pro)
CREATE TABLE integrations (
    id               SERIAL PRIMARY KEY,
    project_id       INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    platform         VARCHAR(20) NOT NULL,   -- telegram | email_smtp
    display_name     VARCHAR(255) NOT NULL,
    encrypted_config TEXT NOT NULL,          -- Fernet-шифрованный JSON с токенами/паролями
    is_active        BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMP DEFAULT NOW()
);

-- ЛОГ ПУБЛИКАЦИЙ
CREATE TABLE publish_logs (
    id                    SERIAL PRIMARY KEY,
    generated_content_id  INTEGER REFERENCES generated_content(id) ON DELETE CASCADE,
    integration_id        INTEGER REFERENCES integrations(id) ON DELETE CASCADE,
    status                VARCHAR(20) NOT NULL,  -- success | failed
    error_message         TEXT,
    published_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_integrations_project ON integrations(project_id);
CREATE INDEX idx_publish_logs_content ON publish_logs(generated_content_id);
