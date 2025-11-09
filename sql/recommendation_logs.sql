CREATE DATABASE IF NOT EXISTS netflix2025;
USE netflix2025;

-- Table for recommendation logs
CREATE TABLE recommendation_logs (
    recommendation_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    movie_id VARCHAR(50) NOT NULL,
    score DECIMAL(5,3),
    clicked BOOLEAN NOT NULL,
    position INT,
    device VARCHAR(50)
);

