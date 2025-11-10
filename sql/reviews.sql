CREATE DATABASE IF NOT EXISTS netflix2025;
USE netflix2025;

-- Table for user search activity
CREATE TABLE reviews (
    review_id BIGINT ,
    user_id BIGINT NOT NULL,
    movie_id BIGINT NOT NULL,
    rating INT NOT NULL,
    review_date DATE NOT NULL,
    device_type VARCHAR(10),
    is_verified BIT,
    total_votes INT,

    PRIMARY KEY (review_id)
);
