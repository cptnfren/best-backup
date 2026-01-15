#!/bin/bash
# Populate PostgreSQL with large dataset for testing

echo "Populating PostgreSQL database with test data..."

docker exec -i test_postgres psql -U postgres -d testdb <<EOF
-- Create test table
CREATE TABLE IF NOT EXISTS test_data (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    age INTEGER,
    salary DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_json JSONB,
    random_text TEXT
);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_test_data_email ON test_data(email);
CREATE INDEX IF NOT EXISTS idx_test_data_created_at ON test_data(created_at);

-- Insert 500,000 rows with random data
INSERT INTO test_data (name, email, age, salary, data_json, random_text)
SELECT 
    'User_' || generate_series,
    'user' || generate_series || '@example.com',
    (random() * 80 + 18)::INTEGER,
    (random() * 100000 + 30000)::DECIMAL(10,2),
    jsonb_build_object(
        'id', generate_series,
        'active', (random() > 0.5),
        'score', (random() * 100)::INTEGER,
        'tags', ARRAY['tag' || (random() * 10)::INTEGER, 'tag' || (random() * 10)::INTEGER]
    ),
    md5(random()::text) || md5(random()::text) || md5(random()::text)
FROM generate_series(1, 500000);

-- Create additional tables
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES test_data(id),
    product_name VARCHAR(255),
    quantity INTEGER,
    price DECIMAL(10,2),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert 100,000 orders
INSERT INTO orders (user_id, product_name, quantity, price, order_date)
SELECT 
    (random() * 500000 + 1)::INTEGER,
    'Product_' || (random() * 1000)::INTEGER,
    (random() * 10 + 1)::INTEGER,
    (random() * 1000 + 10)::DECIMAL(10,2),
    CURRENT_TIMESTAMP - (random() * 365 || ' days')::INTERVAL
FROM generate_series(1, 100000);

-- Analyze tables
ANALYZE test_data;
ANALYZE orders;

-- Show statistics
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    n_live_tup AS row_count
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
EOF

echo "Database population complete!"
