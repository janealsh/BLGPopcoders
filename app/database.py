def get_db():
    try:
        import mysql.connector
    except ImportError as e:
        raise RuntimeError(
            "Missing dependency 'mysql-connector-python'. Install with: pip install mysql-connector-python"
        ) from e

    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Popcoder2025",
        database="netflix2025",
    )
