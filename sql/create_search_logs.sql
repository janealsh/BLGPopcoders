CREATE DATABASE IF NOT EXISTS netflix2025;
USE netflix2025;

-- Table for user search activity
CREATE TABLE search_logs (
    search_id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    search_query VARCHAR(255) NOT NULL,
    search_date DATE NOT NULL,
    clicked_result_position INT,
    location_country VARCHAR(64)
);
