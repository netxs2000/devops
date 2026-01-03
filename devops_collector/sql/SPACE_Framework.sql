
-- Table: satisfaction_records
CREATE TABLE IF NOT EXISTS satisfaction_records (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    score INTEGER NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    tags VARCHAR(255),
    comment VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_satisfaction_date ON satisfaction_records(date);
CREATE INDEX IF NOT EXISTS idx_satisfaction_email ON satisfaction_records(user_email);
