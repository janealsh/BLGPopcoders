from flask import render_template, request , render_template_string, redirect
import mysql.connector
from datetime import date
# removed unused/invalid imports: RecommendationLogs and Movies

# Database connection
db = mysql.connector.connect(
    host= 'localhost',
    user='root',
    password='medo',
    database='netflix2025'
)

cursor = db.cursor()


def home():
    return render_template("home.html")

def movies():
    return render_template("movies.html")


def reviews():
    # Pagination and optional filtering by movie_id and/or user_id
    page_arg = request.args.get('page', '1')
    try:
        page = int(page_arg)
        if page < 1:
            page = 1
    except Exception:
        page = 1

    per_page = 20
    movie_id = request.args.get('movie_id') or None
    user_id = request.args.get('user_id') or None

    where_clauses = []
    params = []
    if movie_id:
        where_clauses.append("reviews.movie_id = %s")
        params.append(movie_id)
    if user_id:
        where_clauses.append("user_id = %s")
        params.append(user_id)

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    try:
        # total count for pagination
        count_sql = f"SELECT COUNT(*) FROM reviews{where_sql}"
        cursor.execute(count_sql, tuple(params))
        total = cursor.fetchone()[0] or 0
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1

        offset = (page - 1) * per_page
        sql = f"""

        
            SELECT reviews.review_id, reviews.user_id, reviews.movie_id, movies.title AS movie_title,
                   reviews.rating, reviews.review_date, reviews.device_type, reviews.is_verified_watch, reviews.total_votes
            FROM reviews
            LEFT JOIN movies ON reviews.movie_id = movies.movie_id
            {where_sql}
            ORDER BY reviews.review_id ASC


            LIMIT %s OFFSET %s
        """
        exec_params = params + [per_page, offset]
        cursor.execute(sql, tuple(exec_params))
        reviews = cursor.fetchall()
        # add a contiguous display index (1-based) that reflects position across pages
        new_reviews = []
        start_index = offset + 1
        for i, row in enumerate(reviews, start=start_index):
            # row is (review_id, user_id, movie_id, movie_title, rating, review_date, device_type, is_verified_watch, total_votes)
            # append display index at the end so templates can show a contiguous number while preserving the real review_id
            new_reviews.append(tuple(list(row) + [i]))
        reviews = new_reviews
        print(f"Fetched {len(reviews)} reviews for page {page}")
    except Exception as e:
        print(f"Error fetching reviews: {e}")
        reviews = []
        total_pages = 1

    return render_template("reviews.html", reviews=reviews, page=page, total_pages=total_pages, movie_id=movie_id, user_id=user_id)


def add_review():
    # required fields (review_id is AUTO_INCREMENT in DB)
    user_id = request.form.get('user_id')
    movie_id = request.form.get('movie_id')
    rating = request.form.get('rating')
    device_type = request.form.get('device_type') or None
    # accept either form field name used in templates
    is_verified_watch = request.form.get('is_verified_watch') if request.form.get('is_verified_watch') is not None else request.form.get('is_verified_watch') or 0
    total_votes = request.form.get('total_votes') or 0

    if not (user_id and movie_id and rating):
        return "Missing required fields", 400

    sql = """
    INSERT INTO reviews (user_id, movie_id, rating, review_date, device_type, is_verified_watch, total_votes)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    values = (user_id, movie_id, rating, date.today(), device_type, is_verified_watch, total_votes)
    try:
        cursor.execute(sql, values)
        db.commit()
    except mysql.connector.Error as e:
        return f"Database error: {e}", 500

    return redirect(f"/reviews?movie_id={movie_id}")


def update_review():
    review_id = request.form.get('review_id')
    rating = request.form.get('rating')
    device_type = request.form.get('device_type')
    is_verified_watch = request.form.get('is_verified_watch') if request.form.get('is_verified_watch') is not None else request.form.get('is_verified_watch') or 0
    total_votes = request.form.get('total_votes') or 0
    movie_id = request.form.get('movie_id')

    if not review_id:
        return "Missing review_id", 400

    sql = """
    UPDATE reviews
    SET rating=%s, device_type=%s, is_verified_watch=%s, total_votes=%s
    WHERE review_id=%s
    """
    values = (rating, device_type, is_verified_watch, total_votes, review_id)
    try:
        cursor.execute(sql, values)
        db.commit()
    except mysql.connector.Error as e:
        return f"Database error: {e}", 500

    return redirect(f"/reviews?movie_id={movie_id}")


def delete_review():
    # prefer deletion by review_id, otherwise by user_id+movie_id
    review_id = request.form.get('review_id')
    if review_id:
        sql = "DELETE FROM reviews WHERE review_id=%s"
        values = (review_id,)
    else:
        user_id = request.form.get('user_id')
        movie_id = request.form.get('movie_id')
        if not (user_id and movie_id):
            return "Missing identifiers for deletion", 400
        sql = "DELETE FROM reviews WHERE user_id=%s AND movie_id=%s"
        values = (user_id, movie_id)

    try:
        cursor.execute(sql, values)
        db.commit()
    except mysql.connector.Error as e:
        return f"Database error: {e}", 500

    # redirect back to the movie reviews page if possible
    movie_id = request.form.get('movie_id') or ''
    return redirect(f"/reviews?movie_id={movie_id}")


def watch_history():
    # db = current_app.config["db"]
    # watch_history = db.watch_history()
    # return render_template("watch_history.html", watch_history = watch_history)

    try: 
        query = """SELECT * FROM watch_history
            ORDER BY watch_date DESC
            LIMIT 100"""
        cursor.execute(query)
        watch_history_data = cursor.fetchall()
        watch_history_columns = [column[0] for column in cursor.fetchall()]

    except mysql.connector.Error as e:
        return f"Database error: {e}. Please check your database and connection, then try again."

    return render_template("watch_history.html", watch_history=watch_history_data, columns=watch_history_columns)



def recommend():
    # Simple recommend view (advanced logic removed to avoid missing module errors)
    return render_template("recommend.html")