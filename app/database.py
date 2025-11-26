import mysql.connector

DB_NAME = "netflix2025"

def get_db():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",          # same as in MySQL Workbench
        password="2003",      # YOUR real MySQL password
        database=DB_NAME,
    )
    return conn
