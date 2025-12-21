import mysql.connector
from mysql.connector import errorcode
import os

# Database configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'PopC.2025'),
    'database': os.environ.get('DB_NAME', 'netflix2025'),
    'port': int(os.environ.get('DB_PORT', 3306)),
}


def get_db():
    """
    Get a database connection.
    Returns a mysql.connector connection object.
    Caller is responsible for closing the connection.
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("ERROR: Database access denied - check username or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("ERROR: Database does not exist")
        else:
            print(f"ERROR: {err}")
        raise


def get_cursor(conn=None):
    """
    Get a database cursor. If conn is provided, use it; otherwise create a new connection.
    Returns a tuple of (connection, cursor).
    Caller is responsible for closing both cursor and connection.
    """
    if conn is None:
        conn = get_db()
    cursor = conn.cursor()
    return conn, cursor