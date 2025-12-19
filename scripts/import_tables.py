import mysql.connector
from mysql.connector import errorcode
import os
import re

# Configuration - match credentials in database.py
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'medo',
    'database': 'netflix2025'
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
            next(file)  # skip header line
            for line in file:
                fields = line.strip().split(',')
                if len(fields) != 6:
                    print(f"Skipping malformed line: {line.strip()}")
                    continue
                
                raw_csv_id = fields[0]
                csv_id = extract_int_id(raw_csv_id)
                email = fields[1].strip() or None
                first_name = fields[2].strip() or None
                gender = fields[3].strip() or None
                subscription_plan = fields[4].strip() or None
                is_active = 1 if fields[5].strip().lower() in ("1", "true", "yes") else 0

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
                    INSERT ignore INTO reviews (review_id, user_id, movie_id, rating, review_date, device_type, is_verified_watch, total_votes)
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


def main():
    import_users_table()
    input("Press Enter to continue to import movies...")
    import_movies_table()
    input("Press Enter to continue to import reviews...")
    import_reviews_table()

if __name__ == "__main__":
    main()
    