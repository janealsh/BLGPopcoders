use CREATE DATABASE IF NOT EXISTS netflix2025;
USE netflix2025;

-- Table for user search activity
CREATE TABLE search_logs (
    search_id BIGINT ,
    user_id BIGINT NOT NULL,
    search_query VARCHAR(255) NOT NULL,
    search_date DATE NOT NULL,
    clicked_result_position INT,
    location_country VARCHAR(64),

    PRIMARY KEY (search_id)
);

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

CREATE TABLE search_history (
    session_id BIGINT ,
    user_id BIGINT NOT NULL,
    movie_id BIGINT NOT NULL,
    watch_date INT NOT NULL,
    watch_duration_minutes INT NOT NULL,
    progress_percentage INT NOT NULL,
    location_country VARCHAR(30),
    user_rating INT,

    PRIMARY KEY (session_id)
    FOREIGN KEY (user_id)
        REFERENCES users
        ON DELETE CASCADE
    FOREIGN KEY (movie_id)
        REFERENCES movies
        ON DELETE CASCADE
);

-- TODO: movies and users table
