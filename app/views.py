from flask import render_template, request , render_template_string, redirect
import mysql.connector
from datetime import date
from recommend import RecommendationLogs
from movies import Movies

# Database connection
db = mysql.connector.connect(
    host= 'localhost',
    user='root',
    password='PopC.2025',
    database='netflix2025'
)

cursor = db.cursor()


def home():
    return render_template("home.html")

def movies():
    try:
        # Watch history'den en çok izlenen 20 filmi getir
        query = """
            SELECT m.movie_id, m.title, m.content_type, m.rating, COUNT(wh.session_id) as watch_count
            FROM movies m
            INNER JOIN watch_history wh ON m.movie_id = wh.movie_id
            GROUP BY m.movie_id, m.title, m.content_type, m.rating
            ORDER BY watch_count DESC
            LIMIT 20
        """
        cursor.execute(query)
        movies_list = cursor.fetchall()
        
        # Tuple'ları dictionary'ye çevir
        movies_data = []
        for movie in movies_list:
            movies_data.append({
                'movie_id': movie[0],
                'title': movie[1],
                'content_type': movie[2],
                'rating': movie[3],
                'watch_count': movie[4]
            })
        
        return render_template("movies.html", movies=movies_data)
    except Exception as e:
        print(f"Error fetching movies: {e}")
        return render_template("movies.html", movies=[], error=str(e))


def movie_detail():
    """Show individual movie details"""
    movie_id = request.args.get('movie_id')
    
    if not movie_id:
        return "Movie ID required", 400
    
    try:
        # Film bilgilerini al
        cursor.execute("SELECT * FROM movies WHERE movie_id = %s", (movie_id,))
        movie = cursor.fetchone()
        
        if not movie:
            return "Movie not found", 404
        
        # Movie tuple'ını dictionary'ye çevir
        movie_data = {
            'movie_id': movie[0],
            'title': movie[1],
            'genre': movie[2] if len(movie) > 2 else None,
            'release_year': movie[3] if len(movie) > 3 else None
        }
        
        # Bu filme ait yorumları al
        cursor.execute("""
            SELECT * FROM reviews 
            WHERE movie_id = %s 
            ORDER BY review_date DESC 
            LIMIT 10
        """, (movie_id,))
        reviews = cursor.fetchall()
        
        return render_template("movie_detail.html", movie=movie_data, reviews=reviews)
    except Exception as e:
        print(f"Error fetching movie detail: {e}")
        return f"Error: {e}", 500



def reviews():
    # Pagination and optional filtering by movie_id and/or user_id
    page_arg = request.args.get('page', '1')
    try:
        page = int(page_arg)
        if page < 1:
            page = 1
    except Exception:
        page = 1

    print("We're here!!")

    per_page = 20
    movie_id = request.args.get('movie_id') or None
    user_id = request.args.get('user_id') or None

    print(f"movie_id: {movie_id}, user_id: {user_id}")

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
            ORDER BY review_date DESC
            LIMIT %s OFFSET %s
        """
        exec_params = params + [per_page, offset]
        cursor.execute(sql, tuple(exec_params))
        reviews = cursor.fetchall()
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

    rec_logs = RecommendationLogs(db)
    movies = Movies(db)

    # Eğer user_id POST ile geldiyse
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        
        if not user_id:
            return render_template("recommend.html", error="Please enter a User ID", show_form=True)
        
        try:
            # Bu kullanıcıya daha önce önerilmiş filmleri getir (ilk 10)
            recommendations = rec_logs.get_user_recommendations(user_id, limit=10)
            
            if not recommendations:
                return render_template("recommend.html", 
                                     error=f"No recommendations found for User ID: {user_id}", 
                                     show_form=True,
                                     user_id=user_id)
            
            # Film başlıklarını al
            movie_titles = []
            for rec in recommendations:
                movie = movies.select_movie(rec['movie_id'])
                if movie:
                    movie_titles.append(movie['title'])
                else:
                    movie_titles.append(f"Unknown Movie (ID: {rec['movie_id']})")
            
            print(f"Recommendations: {len(recommendations)}, Titles: {len(movie_titles)}")
            return render_template("recommend.html", 
                                 recommendations=recommendations, 
                                 movie_titles=movie_titles,
                                 user_id=user_id,
                                 show_form=False)
        except Exception as e:
            print(f"Error fetching recommendations: {e}")
            return render_template("recommend.html", 
                                 error=f"Error: {str(e)}", 
                                 show_form=True)
    
    # İlk yüklemede sadece formu göster
    return render_template("recommend.html", show_form=True)

def save_feedback():
    """Save user feedback (like/dislike) for a recommendation"""
    try:
        # Tüm feedback'leri topla
        feedbacks = []
        index = 0
        
        while True:
            recommendation_id = request.form.get(f'recommendation_id_{index}')
            feedback_type = request.form.get(f'feedback_{index}')
            
            if not recommendation_id:
                break
            
            if feedback_type:  # Sadece feedback verilenleri işle
                feedbacks.append({
                    'recommendation_id': recommendation_id,
                    'feedback_type': feedback_type
                })
            
            index += 1
        
        if not feedbacks:
            return "No feedback provided", 400
        
        # Tüm feedback'leri database'e kaydet
        for feedback in feedbacks:
            update_query = """
                UPDATE recommendation_logs 
                SET is_clicked = 1 
                WHERE recommendation_id = %s
            """
            cursor.execute(update_query, (feedback['recommendation_id'],))
            print(f"Feedback saved: {feedback['recommendation_id']} - {feedback['feedback_type']}")
        
        db.commit()
        print(f"Total {len(feedbacks)} feedbacks saved successfully")
        
    except mysql.connector.Error as e:
        return f"Database error: {e}", 500
    
    # Redirect back to recommend page
    return redirect("/recommend")

def click_recommendation():
    """Mark a recommendation as clicked"""
    recommendation_id = request.form.get('recommendation_id')
    movie_id = request.form.get('movie_id')
    
    if not recommendation_id:
        return "Recommendation ID required", 400
    
    try:
        # is_clicked'i 1 yap
        cursor.execute("""
            UPDATE recommendation_logs 
            SET clicked = 1 
            WHERE recommendation_id = %s
        """, (recommendation_id,))
        db.commit()
        
        # Film detay sayfasına yönlendir
        return redirect(f"/movie?movie_id={movie_id}")
    except Exception as e:
        print(f"Error updating recommendation: {e}")
        return f"Error: {e}", 500