import mysql.connector
from mysql.connector import errorcode

# Configuration - match credentials in database.py
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'PopC.2025',
    'database': 'netflix2025'
}

CREATE_TABLES_SQL = [
    # Users and Movies first (targets of foreign keys)
    # user tables: user_id,email,first_name,gender,subscription_plan,is_active
    (
        "users",
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INT NOT NULL AUTO_INCREMENT,
            email VARCHAR(255),
            first_name VARCHAR(100),
            gender VARCHAR(50),
            subscription_plan VARCHAR(50),
            is_active TINYINT(1) DEFAULT 1,
            PRIMARY KEY (user_id),
            UNIQUE INDEX (email)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
    ),
    (
        "movies",
        """
        CREATE TABLE IF NOT EXISTS movies (
            movie_id INT NOT NULL AUTO_INCREMENT,
            title VARCHAR(255),
            content_type VARCHAR(100),
            rating VARCHAR(20),
            PRIMARY KEY (movie_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
    ),

    # Dependent tables
    (
        "reviews",
        """
        CREATE TABLE IF NOT EXISTS reviews (
            review_id INT NOT NULL AUTO_INCREMENT,
            user_id INT,
            movie_id INT,
            rating TINYINT,
            review_date DATE,
            device_type VARCHAR(50),
            is_verified_watch TINYINT(1),
            total_votes INT DEFAULT 0,
            PRIMARY KEY (review_id),
            INDEX (user_id),
            INDEX (movie_id),
            CONSTRAINT fk_reviews_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL ON UPDATE CASCADE,
            CONSTRAINT fk_reviews_movie FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE SET NULL ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
    ),
    (
        "search_logs",
        """
        CREATE TABLE IF NOT EXISTS search_logs (
            search_id INT NOT NULL AUTO_INCREMENT,
            user_id INT,
            search_query TEXT,
            search_date DATE,
            clicked_result_position INT,
            location_country VARCHAR(100),
            PRIMARY KEY (search_id),
            INDEX (user_id),
            CONSTRAINT fk_search_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
    ),
    (
        "recommendation_logs",
        """
        CREATE TABLE IF NOT EXISTS recommendation_logs (
            recommendation_id VARCHAR(50) NOT NULL,
            user_id INT NOT NULL,
            movie_id INT NOT NULL,
            score DECIMAL(5,3),
            clicked BOOLEAN NOT NULL,
            position INT,
            device VARCHAR(50),
            PRIMARY KEY (recommendation_id),
            INDEX (user_id),
            INDEX (movie_id),
            CONSTRAINT fk_recs_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT fk_recs_movie FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
    ),
    
    (
        "watch_history",
        """
        CREATE TABLE IF NOT EXISTS watch_history (
            session_id VARCHAR(128) NOT NULL,
            user_id INT NOT NULL,
            movie_id INT NOT NULL,
            watch_date DATE,
            watch_duration_minutes DOUBLE,
            progress_percentage DOUBLE,
            location_country VARCHAR(100),
            user_rating INT,

            PRIMARY KEY (session_id),
            INDEX (user_id),
            INDEX (movie_id),
            CONSTRAINT fk_watch_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT fk_watch_movie FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
    ),
]


def create_database_and_tables(config=DB_CONFIG):
    # Connect without specifying database to ensure we can create it if needed
    tmp_cfg = config.copy()
    database_name = tmp_cfg.pop('database', None)

    try:
        cnx = mysql.connector.connect(**tmp_cfg)
        cnx.autocommit = True
        cursor = cnx.cursor()

        if database_name:
            try:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database_name}` DEFAULT CHARACTER SET 'utf8mb4'")
                print(f"Database '{database_name}' ensured (created if missing).")
            except mysql.connector.Error as err:
                print(f"Error creating database '{database_name}': {err}")
                raise

            # Select database for subsequent operations
            try:
                cursor.execute(f"USE `{database_name}`")
            except mysql.connector.Error as err:
                print(f"Error selecting database '{database_name}': {err}")
                raise

        # Drop recommendation_logs if it exists to fix schema issue
        try:
            cursor.execute("DROP TABLE IF EXISTS recommendation_logs")
            print("Dropped existing recommendation_logs table (if any).")
        except mysql.connector.Error as err:
            print(f"Error dropping recommendation_logs: {err}")

        # Create tables in defined order
        for name, stmt in CREATE_TABLES_SQL:
            try:
                cursor.execute(stmt)
                print(f"Table '{name}' created or already exists.")
            except mysql.connector.Error as err:
                print(f"Failed creating table {name}: {err}")
                raise

        try:
            cursor.execute("UPDATE recommendation_logs SET movie_id = REPLACE(movie_id, 'movie_', ''), user_id = REPLACE(user_id, 'user_', '')")
            print("recommendation_logs tablosunda önekler temizlendi.")
        except mysql.connector.Error as err:
            print(f"Önek temizleme sırasında hata: {err}")

    except mysql.connector.Error as err:
        print(f"MySQL error: {err}")
        raise
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            cnx.close()
        except Exception:
            pass


if __name__ == '__main__':
    print("Initializing database and tables (non-destructive)...")
    create_database_and_tables()
    print("Initialization complete.")