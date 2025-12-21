import mysql.connector
import os
from pathlib import Path

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="PopC.2025",
        database="netflix2025"
    )

db_name = "netflix2025"

try:
    NF_DB = mysql.connector.connect(
        host="localhost",       
        user="root",            
        password="PopC.2025",
        allow_local_infile=True
    )

    cursor_NF = NF_DB.cursor()

    cursor_NF.execute("SET GLOBAL local_infile = 1")

    cursor_NF.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
    print(f"Database {db_name} created (if not exists)")

    cursor_NF.execute(f"USE `{db_name}`")
    print(f"Database {db_name} selected.")

    # Yol düzeltmesi: repo köküne göre
    sql_path = Path(__file__).resolve().parents[1] / "sql" / "Tables.sql"
    print(f"Trying SQL file at: {sql_path}")

    if not sql_path.exists():
        raise FileNotFoundError(sql_path)

    with open(sql_path, 'r', encoding='utf-8') as dosya:
        sql_commands = dosya.read()
        commands = [c.strip() for c in sql_commands.split(';') if c.strip()]
        for command in commands:
            if command.startswith('--') or command.startswith('/*'):
                continue
            try:
                cursor_NF.execute(command)
                print("An SQL command executed successfully.")
            except mysql.connector.Error as err:
                print("ERROR executing SQL command:")
                print(err)
                print("Command snippet:")
                print(command[:200])

    print("All tables created from Tables.sql successfully!")

except FileNotFoundError:
    print(f"ERROR: File '{sql_path}' not found. Check the file path.")
except mysql.connector.Error as err:
    print(f"Error: {err}")

finally:
    if 'NF_DB' in locals() and NF_DB.is_connected():
        cursor_NF.close()
        NF_DB.close()

class Database:
    def get_watch_history(self):
        watch_history = []
        return watch_history