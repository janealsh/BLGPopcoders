import os


def get_db_config():
    # Read DB settings from environment variables with sensible defaults
    return {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASSWORD', 'Popcoder2025'),
        'database': os.environ.get('DB_NAME', 'netflix2025'),
        'port': int(os.environ.get('DB_PORT', 3306)),
    }


def get_db():
    try:
        import mysql.connector
    except ImportError as e:
        raise RuntimeError(
            "Missing dependency 'mysql-connector-python'. Install with: pip install mysql-connector-python"
        ) from e

    cfg = get_db_config()
    return mysql.connector.connect(
        host=cfg['host'],
        user=cfg['user'],
        password=cfg['password'],
        database=cfg['database'],
        port=cfg.get('port', 3306),
    )
