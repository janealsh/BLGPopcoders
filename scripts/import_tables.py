import mysql.connector
from mysql.connector import errorcode
import os
import re
import csv

# Configuration - read from environment variables with sensible defaults
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'PopC.2025'),
    'database': os.environ.get('DB_NAME', 'netflix2025'),
    'port': int(os.environ.get('DB_PORT', 3306)),
}


#connect to db
def connect_to_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Data base does not exist")
        else:
            print(err)
    return None


def extract_int_id(s):
    """Extract first integer from a string like 'user_07066' -> 7066. Returns None if not found."""
    if s is None:
        return None
    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else None


def create_mapping_tables(conn):
    """Create mapping tables used during import: import_user_map and import_movie_map."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS import_user_map (
            csv_id INT PRIMARY KEY,
            user_id INT NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS import_movie_map (
            csv_id INT PRIMARY KEY,
            movie_id INT NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    conn.commit()
    cur.close()

def import_users_table():
    conn = connect_to_db()
    if conn is None:
        print("Failed to connect to the database.")
        return

    create_mapping_tables(conn)
    cursor = conn.cursor()

    # read csv file from tables folder
    csv_file_path = os.path.join(os.path.dirname(__file__), '../Tables/users.csv')

    # user_id,email,first_name,gender,subscription_plan,is_active
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                raw_csv_id = row['user_id']
                csv_id = extract_int_id(raw_csv_id)
                email = row['email'].strip() if row['email'] else None
                first_name = row['first_name'].strip() if row['first_name'] else None
                gender = row['gender'].strip() if row['gender'] else None
                subscription_plan = row['subscription_plan'].strip() if row['subscription_plan'] else None
                is_active = 1 if row['is_active'].strip() in ("1", "true", "yes", "True", "Yes", "YES") else 0

                # Try to find canonical user by normalized email
                user_id = None
                if email:
                    cursor.execute("SELECT user_id FROM users WHERE LOWER(TRIM(email)) = %s LIMIT 1", (email.lower().strip(),))
                    res = cursor.fetchone()
                    if res:
                        user_id = res[0]

                # If not found, insert new user (let auto-increment assign id)
                if user_id is None:
                    insert_query = """
                        INSERT INTO users (email, first_name, gender, subscription_plan, is_active)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, (email, first_name, gender, subscription_plan, is_active))
                    user_id = cursor.lastrowid

                # persist mapping CSV id -> canonical user_id
                if csv_id is not None:
                    cursor.execute("REPLACE INTO import_user_map (csv_id, user_id) VALUES (%s, %s)", (csv_id, user_id))
            conn.commit()
            print("Users data imported successfully.")
    except FileNotFoundError:
        print(f"ERROR: File '{csv_file_path}' not found. Check the file path.")
    except mysql.connector.Error as err:
        print(f"Error importing users data: {err}")
    finally:
        cursor.close()
        conn.close()


def import_movies_table():

    conn = connect_to_db()
    if conn is None:
        print("Failed to connect to the database.")
        return

    create_mapping_tables(conn)
    cursor = conn.cursor()

    # read csv file from tables folder
    csv_file_path = os.path.join(os.path.dirname(__file__), '../Tables/movies.csv')

    # movie_id,title,content_type,rating
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            next(file)  # skip header line
            for line in file:
            
                fields = line.strip().split(',')
                if len(fields) != 4:
                    print(f"Skipping malformed line: {line.strip()}")
                    continue

                raw_csv_id = fields[0]
                csv_id = extract_int_id(raw_csv_id)
                title = fields[1].strip() or None
                content_type = fields[2].strip() or None
                rating = fields[3].strip() or None

                # find existing canonical movie by normalized title+content_type
                movie_id = None
                if title:
                    cursor.execute(
                        "SELECT movie_id FROM movies WHERE LOWER(TRIM(title)) = %s AND LOWER(TRIM(COALESCE(content_type,''))) = %s LIMIT 1",
                        (title.lower().strip(), (content_type or '').lower().strip())
                    )
                    res = cursor.fetchone()
                    if res:
                        movie_id = res[0]

                if movie_id is None:
                    insert_query = """
                        INSERT INTO movies (title, content_type, rating)
                        VALUES (%s, %s, %s)
                    """
                    cursor.execute(insert_query, (title, content_type, rating))
                    movie_id = cursor.lastrowid

                if csv_id is not None:
                    cursor.execute("REPLACE INTO import_movie_map (csv_id, movie_id) VALUES (%s, %s)", (csv_id, movie_id))
            conn.commit()
            print("Movies data imported successfully.")
    except FileNotFoundError:
        print(f"ERROR: File '{csv_file_path}' not found. Check the file path.")
    except mysql.connector.Error as err:
        print(f"Error importing movies data: {err}")
    finally:
        cursor.close()
        conn.close()

def import_reviews_table():

    conn = connect_to_db()
    if conn is None:
        print("Failed to connect to the database.")
        return

    cursor = conn.cursor()

    # read csv file from tables folder
    csv_file_path = os.path.join(os.path.dirname(__file__), '../Tables/reviews.csv')

    # review_id,user_id,movie_id,rating,review_date,device_type,is_verified_watch,total_votes

    # parse review_id column by removing prefix "review_"
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            next(file)  # skip header line
            for line in file:
                fields = line.strip().split(',')
                if len(fields) != 8:
                    print(f"Skipping malformed line: {line.strip()}")
                    continue

                review_csv_id = extract_int_id(fields[0])
                user_csv_id = extract_int_id(fields[1])
                movie_csv_id = extract_int_id(fields[2])

                # map CSV ids -> canonical ids using import_*_map tables
                mapped_user_id = None
                mapped_movie_id = None

                if user_csv_id is not None:
                    cursor.execute("SELECT user_id FROM import_user_map WHERE csv_id = %s LIMIT 1", (user_csv_id,))
                    r = cursor.fetchone()
                    if r:
                        mapped_user_id = r[0]
                    else:
                        # fallback: check if numeric id exists in users table
                        cursor.execute("SELECT user_id FROM users WHERE user_id = %s LIMIT 1", (user_csv_id,))
                        r2 = cursor.fetchone()
                        if r2:
                            mapped_user_id = r2[0]

                if movie_csv_id is not None:
                    cursor.execute("SELECT movie_id FROM import_movie_map WHERE csv_id = %s LIMIT 1", (movie_csv_id,))
                    r = cursor.fetchone()
                    if r:
                        mapped_movie_id = r[0]
                    else:
                        cursor.execute("SELECT movie_id FROM movies WHERE movie_id = %s LIMIT 1", (movie_csv_id,))
                        r2 = cursor.fetchone()
                        if r2:
                            mapped_movie_id = r2[0]

                rating = int(fields[3]) if fields[3] else None
                review_date = fields[4] or None
                device_type = fields[5] or None
                is_verified_watch = 1 if fields[6].strip().lower() in ("1", "true", "yes") else 0
                total_votes = int(float(fields[7])) if fields[7] not in ("", None) else 0

                insert_query = """
                    REPLACE INTO reviews (review_id, user_id, movie_id, rating, review_date, device_type, is_verified_watch, total_votes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (review_csv_id, mapped_user_id, mapped_movie_id, rating, review_date, device_type, is_verified_watch, total_votes))

            conn.commit()
            print("Reviews data imported successfully.")

    except FileNotFoundError:
        print(f"ERROR: File '{csv_file_path}' not found. Check the file path.")
    except mysql.connector.Error as err:
        print(f"Error importing reviews data: {err}")
    finally:
        cursor.close()
        conn.close()


def import_search_logs_table():
    conn = connect_to_db()
    if conn is None:
        print("Failed to connect to the database.")
        return

    cursor = conn.cursor()
    csv_file_path = os.path.join(os.path.dirname(__file__), '../Tables/search_logs.csv')

    # search_logs CSV columns (assumed): search_id,user_id,search_query,search_date,clicked_result_position,location_country
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            next(file)  # skip header
            for line in file:
                fields = line.strip().split(',')
                if len(fields) < 4:  # minimum fields required
                    continue

                search_csv_id = extract_int_id(fields[0]) if len(fields) > 0 else None
                user_csv_id = extract_int_id(fields[1]) if len(fields) > 1 else None
                search_query = fields[2].strip() if len(fields) > 2 else None
                search_date = fields[3].strip() if len(fields) > 3 else None
                clicked_pos = int(fields[4]) if len(fields) > 4 and fields[4].strip() else None
                location_country = fields[5].strip() if len(fields) > 5 else None

                # map user_csv_id to canonical user_id using import_user_map
                mapped_user_id = None
                if user_csv_id is not None:
                    cursor.execute("SELECT user_id FROM import_user_map WHERE csv_id = %s LIMIT 1", (user_csv_id,))
                    r = cursor.fetchone()
                    if r:
                        mapped_user_id = r[0]
                    else:
                        # fallback: try direct id match in users table
                        cursor.execute("SELECT user_id FROM users WHERE user_id = %s LIMIT 1", (user_csv_id,))
                        r2 = cursor.fetchone()
                        if r2:
                            mapped_user_id = r2[0]

                insert_query = """
                    REPLACE INTO search_logs (search_id, user_id, search_query, search_date, clicked_result_position, location_country)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (search_csv_id, mapped_user_id, search_query, search_date, clicked_pos, location_country))

            conn.commit()
            print("Search logs data imported successfully.")
    except FileNotFoundError:
        print(f"ERROR: File '{csv_file_path}' not found. Check the file path.")
    except mysql.connector.Error as err:
        print(f"Error importing search_logs data: {err}")
    finally:
        cursor.close()
        conn.close()


def import_watch_history_table():
    conn = connect_to_db()
    if conn is None:
        print("Failed to connect to the database.")
        return

    cursor = conn.cursor()
    csv_file_path = os.path.join(os.path.dirname(__file__), '../Tables/watch_history.csv')

    # session_id,user_id,movie_id,watch_date,watch_duration_minutes,progress_percentage,location_country,rating
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                session_id = row['session_id'].strip() if row['session_id'] else None
                user_csv_id = extract_int_id(row['user_id']) if row['user_id'] else None
                movie_csv_id = extract_int_id(row['movie_id']) if row['movie_id'] else None
                watch_date = row['watch_date'].strip() if row['watch_date'] else None
                watch_duration = float(row['watch_duration_minutes']) if row['watch_duration_minutes'].strip() else None
                progress_pct = float(row['progress_percentage']) if row['progress_percentage'].strip() else None
                location_country = row['location_country'].strip() if row['location_country'] else None
                user_rating = int(row['rating']) if row['rating'].strip() else None

                mapped_user_id = None
                mapped_movie_id = None

                if user_csv_id is not None:
                    cursor.execute("SELECT user_id FROM import_user_map WHERE csv_id = %s LIMIT 1", (user_csv_id,))
                    r = cursor.fetchone()
                    if r:
                        mapped_user_id = r[0]
                    else:
                        cursor.execute("SELECT user_id FROM users WHERE user_id = %s LIMIT 1", (user_csv_id,))
                        r2 = cursor.fetchone()
                        if r2:
                            mapped_user_id = r2[0]

                if movie_csv_id is not None:
                    cursor.execute("SELECT movie_id FROM import_movie_map WHERE csv_id = %s LIMIT 1", (movie_csv_id,))
                    r = cursor.fetchone()
                    if r:
                        mapped_movie_id = r[0]
                    else:
                        cursor.execute("SELECT movie_id FROM movies WHERE movie_id = %s LIMIT 1", (movie_csv_id,))
                        r2 = cursor.fetchone()
                        if r2:
                            mapped_movie_id = r2[0]

                insert_query = """
                    REPLACE INTO watch_history (session_id, user_id, movie_id, watch_date, watch_duration_minutes, progress_percentage, location_country, user_rating)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (session_id, mapped_user_id, mapped_movie_id, watch_date, watch_duration, progress_pct, location_country, user_rating))

            conn.commit()
            print("Watch history data imported successfully.")
    except FileNotFoundError:
        print(f"ERROR: File '{csv_file_path}' not found. Check the file path.")
    except mysql.connector.Error as err:
        print(f"Error importing watch_history data: {err}")
    finally:
        cursor.close()
        conn.close()


def import_recommendation_logs_table():
    conn = connect_to_db()
    if conn is None:
        print("Failed to connect to the database.")
        return

    cursor = conn.cursor()
    csv_file_path = os.path.join(os.path.dirname(__file__), '../Tables/recommendation_logs.csv')

    # CSV format (no header): rec_id,user_id,movie_id,score,clicked,position,device
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for fields in reader:
                if len(fields) < 3:
                    continue
                    
                rec_id = fields[0].strip() if len(fields) > 0 and fields[0] else None
                user_csv_id = extract_int_id(fields[1]) if len(fields) > 1 and fields[1] else None
                movie_csv_id = extract_int_id(fields[2]) if len(fields) > 2 and fields[2] else None
                score = float(fields[3]) if len(fields) > 3 and fields[3].strip() else None
                is_clicked = 1 if len(fields) > 4 and fields[4].strip().lower() in ("1", "true", "yes", "True", "Yes") else 0
                rank = int(fields[5]) if len(fields) > 5 and fields[5].strip() else None
                device_type = fields[6].strip() if len(fields) > 6 and fields[6] else None

                # map user_csv_id and movie_csv_id to canonical IDs
                mapped_user_id = None
                mapped_movie_id = None

                if user_csv_id is not None:
                    cursor.execute("SELECT user_id FROM import_user_map WHERE csv_id = %s LIMIT 1", (user_csv_id,))
                    r = cursor.fetchone()
                    if r:
                        mapped_user_id = r[0]
                    else:
                        cursor.execute("SELECT user_id FROM users WHERE user_id = %s LIMIT 1", (user_csv_id,))
                        r2 = cursor.fetchone()
                        if r2:
                            mapped_user_id = r2[0]

                if movie_csv_id is not None:
                    cursor.execute("SELECT movie_id FROM import_movie_map WHERE csv_id = %s LIMIT 1", (movie_csv_id,))
                    r = cursor.fetchone()
                    if r:
                        mapped_movie_id = r[0]
                    else:
                        cursor.execute("SELECT movie_id FROM movies WHERE movie_id = %s LIMIT 1", (movie_csv_id,))
                        r2 = cursor.fetchone()
                        if r2:
                            mapped_movie_id = r2[0]

                insert_query = """
                    REPLACE INTO recommendation_logs (recommendation_id, user_id, movie_id, score, clicked, position, device)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (rec_id, mapped_user_id, mapped_movie_id, score, is_clicked, rank, device_type))

            conn.commit()
            print("Recommendation logs data imported successfully.")
    except FileNotFoundError:
        print(f"ERROR: File '{csv_file_path}' not found. Check the file path.")
    except mysql.connector.Error as err:
        print(f"Error importing recommendation_logs data: {err}")
    finally:
        cursor.close()
        conn.close()

def drop_mapping_tables():
    conn = connect_to_db()
    if conn is None:
        return

    cursor = conn.cursor()
    try:
        cursor.execute("DROP TABLE IF EXISTS import_user_map")
        cursor.execute("DROP TABLE IF EXISTS import_movie_map")
        conn.commit()
        print("Mapping tables dropped successfully.")
    except mysql.connector.Error as err:
        print(f"Error dropping mapping tables: {err}")
    finally:
        cursor.close()
        conn.close()


def main():
    import_users_table()
    input("Press Enter to continue to import movies...")
    import_movies_table()
    input("Press Enter to continue to import reviews...")
    import_reviews_table()
    input("Press Enter to continue to import search_logs...")
    import_search_logs_table()
    input("Press Enter to continue to import watch_history...")
    import_watch_history_table()
    input("Press Enter to continue to import recommendation_logs...")
    import_recommendation_logs_table()
    drop_mapping_tables()
if __name__ == "__main__":
    main()
    