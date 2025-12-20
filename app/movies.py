import os

class Movies:
    def __init__(self, connection):
        self.columns = ['movie_id', 'title', 'content_type', 'rating']
        self.connection = connection

    def load_movies_from_csv(self):
        try:
            cursor = self.connection.cursor()
            
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            csv_path = os.path.join(base_dir, 'Tables', 'movies.csv')
            
            query = f"""
                LOAD DATA LOCAL INFILE '{csv_path}'
                INTO TABLE movies
                FIELDS TERMINATED BY ',' 
                LINES TERMINATED BY '\\n'
                IGNORE 1 ROWS
                (movie_id, title, content_type, rating);
            """
            
            cursor.execute(query)
            self.connection.commit()
            cursor.close()
            
            print(f"Success: Data loaded from {csv_path}")

        except Exception as e:
            print(f"Error loading CSV: {e}")

    def generate_primary_key(self):
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT MAX(movie_id) FROM movies")
            max_id = cursor.fetchone()[0]
            cursor.close()
            
            if max_id is None:
                return "movie_000001"
            
            prefix = "movie_"
            try:
                if max_id.startswith(prefix):
                    number_part = int(max_id[len(prefix):])
                    new_number = number_part + 1
                    return f"{prefix}{new_number:06d}"
                else:
                    return f"{prefix}000001"
            except ValueError:
                return f"{prefix}000001"

        except Exception as e:
            print("Error while generating primary key for movies", e)
            return f"Error: {e}"

    def insert_movie(self, data):
        try:
            cursor = self.connection.cursor()

            data['movie_id'] = self.generate_primary_key()

            for key, value in data.items():
                if value == 'None' or value == '':
                    data[key] = None

            insert_fields = ', '.join(self.columns)
            placeholders = ', '.join(['%s' for _ in self.columns])
            insert_query = f"INSERT INTO movies ({insert_fields}) VALUES ({placeholders})"

            insert_values = [data.get(col) for col in self.columns]

            cursor.execute(insert_query, tuple(insert_values))
            self.connection.commit()
            cursor.close()
            print("Inserted", insert_values)
        except Exception as e:
            print("Error while inserting into movies", e)
            return f"Error: {e}"

    def update_movie(self, data, movie_id):
        try:
            cursor = self.connection.cursor()
            processed_data = [
                None if data.get(field) == 'None' else data.get(field) 
                for field in self.columns if field in data
            ]
            update_fields = ', '.join([f"{field} = %s" for field in self.columns if field in data])
            
            update_query = f"UPDATE movies SET {update_fields} WHERE movie_id = %s"
            
            if processed_data:
                cursor.execute(update_query, processed_data + [movie_id])
                self.connection.commit()
                print("Updated", processed_data)
            cursor.close()
        except Exception as e:
            print("Error while updating movies", e)
            return f"Error: {e}"

    def delete_movie(self, movie_id):
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM movies WHERE movie_id=%s", (movie_id,))
            self.connection.commit()
            cursor.close()
            print("Deleted", movie_id)
        except Exception as e:
            print("Error while deleting from movies", e)
            return f"Error: {e}"

    def search_movies(self, data):
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
            
            query = "SELECT * FROM movies WHERE " + " AND ".join(query_parts)
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

    def select_movie(self, movie_id):
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = "SELECT * FROM movies WHERE movie_id = %s"
            cursor.execute(query, (movie_id,))
            result = cursor.fetchone()
            cursor.close()
            return result
        except Exception as e:
            print(f"Error fetching movie {movie_id}: {e}")
            return None