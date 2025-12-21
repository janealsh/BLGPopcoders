import os
import sys
import argparse
import mysql.connector

# Ensure we can import init_db from the same folder
sys.path.append(os.path.dirname(__file__))
try:
    import init_db
    DB_CONFIG = init_db.DB_CONFIG
except Exception:
    # fallback - copy your DB config here if import fails
    DB_CONFIG = {
        'host': 'localhost',
        'user': 'root',
        'password': 'medo',
        'database': 'netflix2025'
    }


def column_exists(cursor, table, column):
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (DB_CONFIG['database'], table, column),
    )
    return cursor.fetchone()[0] > 0


def constraint_exists(cursor, table, constraint_name):
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS "
        "WHERE CONSTRAINT_SCHEMA = %s AND TABLE_NAME = %s AND CONSTRAINT_NAME = %s",
        (DB_CONFIG['database'], table, constraint_name),
    )
    return cursor.fetchone()[0] > 0


def migrate(drop_old=False):
    cnx = mysql.connector.connect(**DB_CONFIG)
    cnx.autocommit = False
    cursor = cnx.cursor()
    try:
        # 1) Ensure devices table exists
        cursor.execute("CREATE TABLE IF NOT EXISTS devices (device_id INT NOT NULL AUTO_INCREMENT, device_type VARCHAR(100) UNIQUE, PRIMARY KEY (device_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;")

        # 2) Insert distinct device_type values from reviews into devices
        cursor.execute(
            "INSERT IGNORE INTO devices (device_type) SELECT DISTINCT device_type FROM reviews WHERE device_type IS NOT NULL AND device_type <> ''"
        )
        print(f"Inserted/ensured device types in 'devices' table: {cursor.rowcount} rows (may include duplicates ignored).")

        # Also insert distinct device types found in recommendation_logs (if present)
        try:
            cursor.execute(
                "INSERT IGNORE INTO devices (device_type) SELECT DISTINCT device_type FROM recommendation_logs WHERE device_type IS NOT NULL AND device_type <> ''"
            )
            print(f"Inserted/ensured device types from recommendation_logs: {cursor.rowcount} rows (may include duplicates ignored).")
        except mysql.connector.Error:
            # table or column may not exist yet; ignore
            pass

        # 3) Add device_id column to reviews if missing
        if not column_exists(cursor, 'reviews', 'device_id'):
            cursor.execute("ALTER TABLE reviews ADD COLUMN device_id INT NULL;")
            print("Added 'device_id' column to 'reviews'.")

        # 4) Populate reviews.device_id by joining on device_type
        cursor.execute(
            "UPDATE reviews r JOIN devices d ON r.device_type = d.device_type SET r.device_id = d.device_id WHERE r.device_type IS NOT NULL AND r.device_type <> ''"
        )
        print(f"Updated reviews.device_id for {cursor.rowcount} rows.")

        # Migrate recommendation_logs.device_type -> recommendation_logs.device_id when applicable
        try:
            # add device_id column if missing
            if not column_exists(cursor, 'recommendation_logs', 'device_id'):
                cursor.execute("ALTER TABLE recommendation_logs ADD COLUMN device_id INT NULL;")
                print("Added 'device_id' column to 'recommendation_logs'.")

            # populate device_id by joining on device_type
            cursor.execute(
                "UPDATE recommendation_logs r JOIN devices d ON r.device_type = d.device_type SET r.device_id = d.device_id WHERE r.device_type IS NOT NULL AND r.device_type <> ''"
            )
            print(f"Updated recommendation_logs.device_id for {cursor.rowcount} rows.")

            # add index and FK if possible
            try:
                cursor.execute("ALTER TABLE recommendation_logs ADD INDEX idx_recs_device_id (device_id)")
            except mysql.connector.Error:
                pass
            if not constraint_exists(cursor, 'recommendation_logs', 'fk_recs_device'):
                try:
                    cursor.execute(
                        "ALTER TABLE recommendation_logs ADD CONSTRAINT fk_recs_device FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE SET NULL ON UPDATE CASCADE"
                    )
                    print("Added foreign key constraint fk_recs_device.")
                except mysql.connector.Error:
                    pass

            # optionally drop old column
            if drop_old and column_exists(cursor, 'recommendation_logs', 'device_type'):
                cursor.execute("ALTER TABLE recommendation_logs DROP COLUMN device_type")
                print("Dropped old 'device_type' column from 'recommendation_logs'.")
        except mysql.connector.Error:
            # recommendation_logs may not exist or other issue; ignore and continue
            pass

        # 5) Add index on device_id (if not present) - we attempt and ignore errors
        try:
            cursor.execute("ALTER TABLE reviews ADD INDEX idx_reviews_device_id (device_id)")
            print("Added index on reviews(device_id).")
        except mysql.connector.Error:
            print("Index on reviews(device_id) already exists or could not be added (continuing).")

        # 6) Add foreign key constraint if missing
        if not constraint_exists(cursor, 'reviews', 'fk_reviews_device'):
            try:
                cursor.execute(
                    "ALTER TABLE reviews ADD CONSTRAINT fk_reviews_device FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE SET NULL ON UPDATE CASCADE"
                )
                print("Added foreign key constraint fk_reviews_device.")
            except mysql.connector.Error as e:
                print(f"Could not add FK constraint: {e}")

        # 7) Optionally drop the old device_type column
        if drop_old and column_exists(cursor, 'reviews', 'device_type'):
            cursor.execute("ALTER TABLE reviews DROP COLUMN device_type")
            print("Dropped old 'device_type' column from 'reviews'.")

        cnx.commit()
        print("Migration completed successfully.")

    except mysql.connector.Error as e:
        cnx.rollback()
        print(f"Database error during migration: {e}")
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
    ap = argparse.ArgumentParser(description='Migrate reviews.device_type into devices and populate reviews.device_id')
    ap.add_argument('--drop', action='store_true', help='Drop the old device_type column after migrating')
    args = ap.parse_args()

    migrate(drop_old=args.drop)
