class RecommendationLogs:
    def __init__(self, connection):
        # column names aligned with the schema in init_db.py
        self.columns = ['rec_id', 'user_id', 'movie_id', 'score', 'is_clicked', 'rank', 'device_type']
        self.connection = connection

    def generate_primary_key(self):
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT MAX(rec_id) FROM recommendation_logs")
            max_id = cursor.fetchone()[0]
            cursor.close()
            
            if max_id is None:
                return "rec_000001"
            
            prefix = "rec_"
            try:
                if isinstance(max_id, str) and max_id.startswith(prefix):
                    number_part = int(max_id[len(prefix):])
                    new_number = number_part + 1
                    return f"{prefix}{new_number:06d}"
                else:
                    return f"{prefix}000001"
            except ValueError:
                return f"{prefix}000001"

        except Exception as e:
            print("Error while generating primary key for recommendation_logs", e)
            return None

    def insert_data(self, data):
        try:
            cursor = self.connection.cursor()

            new_id = self.generate_primary_key()
            data['rec_id'] = new_id

            for key, value in data.items():
                if value == 'None' or value == '':
                    data[key] = None

            insert_fields = ', '.join(self.columns)
            placeholders = ', '.join(['%s' for _ in self.columns])
            insert_query = f"INSERT INTO recommendation_logs ({insert_fields}) VALUES ({placeholders})"

            insert_values = [data.get(col) for col in self.columns]

            cursor.execute(insert_query, tuple(insert_values))
            self.connection.commit()
            cursor.close()
            print("Inserted", insert_values)
        except Exception as e:
            print("Error while inserting into recommendation_logs", e)
            return f"Error: {e}"

    def update_data(self, data, recommendation_id):
        try:
            cursor = self.connection.cursor()
            processed_data = [
                None if data.get(field) == 'None' else data.get(field)
                for field in self.columns if field in data
            ]
            update_fields = ', '.join([f"{field} = %s" for field in self.columns if field in data])

            update_query = f"UPDATE recommendation_logs SET {update_fields} WHERE rec_id = %s"

            if processed_data:
                cursor.execute(update_query, processed_data + [recommendation_id])
                self.connection.commit()
                print("Updated", processed_data)
            cursor.close()
        except Exception as e:
            print("Error while updating recommendation_logs", e)
            return f"Error: {e}"

    def delete_data(self, recommendation_id):
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM recommendation_logs WHERE rec_id=%s", (recommendation_id,))
            self.connection.commit()
            cursor.close()
            print("Deleted", recommendation_id)
        except Exception as e:
            print("Error while deleting from recommendation_logs", e)
            return f"Error: {e}"

    def search(self, data):
        try:
            cursor = self.connection.cursor()
            query_parts = []
            parameters = []
            for column in self.columns:
                value = str(data.get(column, '')) + '%'
                if value == '%':
                    query_parts.append(f"({column} LIKE %s OR {column} IS NULL)")
                else:
                    query_parts.append(f"{column} LIKE %s")
                parameters.append(value)
            
            query = "SELECT * FROM recommendation_logs WHERE " + " AND ".join(query_parts)
            cursor.execute(query, tuple(parameters))
            results = cursor.fetchall()
            columns = cursor.description 
            cursor.close()
            
            column_types = []
            for column in columns:
                column_name = column[0]
                column_type = column[1]
                try:
                    if 'get_mysql_data_types' in globals():
                        mysql_data_type = get_mysql_data_types(column_type)
                    else:
                        mysql_data_type = str(column_type)
                except:
                    mysql_data_type = str(column_type)
                
                item = {'column_name': column_name, 'column_type': mysql_data_type}
                column_types.append(item)
            return results, column_types
        
        except Exception as e:
            print("Could not find any corresponding value", e)
            return False