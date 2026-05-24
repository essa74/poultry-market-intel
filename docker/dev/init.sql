-- Initialize poultry_market database schema

CREATE TABLE IF NOT EXISTS price_records (
    id SERIAL PRIMARY KEY,
    product_type VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    currency VARCHAR(10) DEFAULT 'EGP',
    unit VARCHAR(30) NOT NULL,
    market VARCHAR(100),
    region VARCHAR(100),
    recorded_date DATE NOT NULL,
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_price_records_product_type ON price_records(product_type);
CREATE INDEX idx_price_records_recorded_date ON price_records(recorded_date);
CREATE INDEX idx_price_records_product_date ON price_records(product_type, recorded_date);

CREATE TABLE IF NOT EXISTS holiday_calendar (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    date DATE NOT NULL UNIQUE,
    holiday_type VARCHAR(50) NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    product_type VARCHAR(50) NOT NULL,
    predicted_price DOUBLE PRECISION NOT NULL,
    predicted_date DATE NOT NULL,
    confidence_lower DOUBLE PRECISION,
    confidence_upper DOUBLE PRECISION,
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_predictions_product_type ON predictions(product_type);
CREATE INDEX idx_predictions_date ON predictions(predicted_date);
