import os, mysql.connector
cfg = {
  'host': os.environ.get('DB_HOST','localhost'),
  'user': os.environ.get('DB_USER','root'),
  'password': os.environ.get('DB_PASSWORD','Popcoder2025'),
  'database': os.environ.get('DB_NAME','netflix2025'),
  'port': int(os.environ.get('DB_PORT',3306))
}
cnx = mysql.connector.connect(**cfg)
cur = cnx.cursor()
for t in ('users','movies','reviews'):
    try:
        cur.execute(f"SHOW CREATE TABLE {t}")
        row = cur.fetchone()
        print('\\n---', t, '---\\n')
        print(row[1])
    except Exception as e:
        print('\\nERROR for', t, ':', e)
cur.close(); cnx.close()