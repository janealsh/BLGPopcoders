import os


def get_db_config():
    # Read DB settings from environment variables with sensible defaults
    return {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASSWORD', 'medo'),
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
import mysql.connector
from pathlib import Path

def get_db_connection():
    cfg = get_db_config()
    return mysql.connector.connect(
        host=cfg['host'],
        user=cfg['user'],
        password=cfg['password'],
        database=cfg['database'],
        port=cfg.get('port', 3306),
        allow_local_infile=True,
    )

def initialize_database_from_sql(sql_path=None, config=None):
    if config is None:
        config = get_db_config()
    if sql_path is None:
        sql_path = Path(__file__).resolve().parents[1] / 'sql' / 'Tables.sql'

    cnx = None
    cursor = None
    try:
        cnx = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            port=config.get('port', 3306),
            allow_local_infile=True,
        )
        cursor = cnx.cursor()
        cursor.execute("SET GLOBAL local_infile = 1")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{config['database']}`")
        cursor.execute(f"USE `{config['database']}`")

        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_commands = f.read()
        commands = [c.strip() for c in sql_commands.split(';') if c.strip()]
        for command in commands:
            if command.startswith('--') or command.startswith('/*'):
                continue
            cursor.execute(command)
        cnx.commit()
        print(f"Executed SQL file: {sql_path}")
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if cnx:
                cnx.close()
        except Exception:
            pass

class Database:
    def get_watch_history(self):
        return []
