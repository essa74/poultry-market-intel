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
    name_ar VARCHAR(200) NOT NULL,
    name_en VARCHAR(200) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    impact_description VARCHAR(200),
    impact_percentage DOUBLE PRECISION,
    affected_products JSONB,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_holiday_calendar_event_type ON holiday_calendar(event_type);
CREATE INDEX IF NOT EXISTS idx_holiday_calendar_start_date ON holiday_calendar(start_date);

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
