CREATE DATABASE IF NOT EXISTS netflix2025;
USE netflix2025;

-- Table for user search activity
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
