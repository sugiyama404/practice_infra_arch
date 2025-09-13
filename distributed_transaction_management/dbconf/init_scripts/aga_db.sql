USE saga_orchestrator;

CREATE TABLE IF NOT EXISTS workflows (
    workflow_id VARCHAR(36) PRIMARY KEY,
    status VARCHAR(20) NOT NULL,
    activities TEXT NOT NULL,
    current_activity_index INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    error TEXT,
    result TEXT
);