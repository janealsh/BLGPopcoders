import mysql.connector
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Popcoder2025",
        database="netflix2025"
    )
