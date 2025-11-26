import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="medo",
        database="netflix2025"
    )

"""

import mysql.connector
import os

from watch_history import WatchHistory

db_name = "netflix2025"

try:
    NF_DB = mysql.connector.connect(
        host="localhost",       
        user="root",            
        password="medo",
    )


    cursor_NF = NF_DB.cursor()

    cursor_NF.execute(f"DROP DATABASE IF EXISTS {db_name}")
    cursor_NF.execute(f"CREATE DATABASE {db_name}")
    print(f"Database {db_name} created")

    cursor_NF.execute(f"USE {db_name}")
    print(f"Database {db_name}  selected.")

    sql_path = '../sql/Tables.sql'

    try:
        with open(sql_path, 'r', encoding='utf-8') as dosya:
            sql_commands= dosya.read()
            
            commands = sql_commands.split(';')
            
            for command in commands:
                if command.strip():
                    cursor_NF.execute(command)
                    print("An SQL command executed successfully.")
                    
        print("All tables created from Tables.sql successfully!")

    except FileNotFoundError:
        print(f"ERROR: File '{sql_path}' not found.Check the file path.")
    except mysql.connector.Error as err:
        print(f"Error creating tables: {err}")

    if (NF_DB.is_connected()):
        cursor_NF.close()   
        NF_DB.close()

except mysql.connector.Error as err:
    print(f"Error: {err}")



class Database:
    # def __init__(self, title, date_time, user):

    def get_watch_history(self):
        watch_history = []
        return
"""