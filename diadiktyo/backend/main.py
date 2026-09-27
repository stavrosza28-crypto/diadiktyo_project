from fastapi import FastAPI, Query #το framework για τη δημιουργια του API
from fastapi.middleware.cors import CORSMiddleware # απαραίτητο για αιτήσεις από διαφορετικό origin
from pydantic import BaseModel  # για ορισμό των δομών δεδομένων που θα λαμβάνουμε στο POST 
import sqlite3 # για σύνδεση και αλληλεπίδραση με τη βάση δεδομένων SQLite
from typing import List # για να ορίσουμε λίστες στα μοντέλα δεδομένων
import pandas as pd # για διαχείριση των δεδομένων από τη βάση με ευκολία (DataFrames)
import math # για τον υπολογισμό της τετραγωνικής ρίζας στο Pearson Correlation

app = FastAPI() # δημιουργία του FastAPI app instance




# Ενεργοποίηση CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "movielens.db"# το όνομα της βάσης δεδομένων που θα χρησιμοποιήσουμε

# Βοηθητική συνάρτηση για σύνδεση στη βάση
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    # Αυτό μας επιτρέπει να παίρνουμε τα αποτελέσματα σαν λεξικά (dictionaries) αντί για απλές λίστες
    conn.row_factory = sqlite3.Row 
    return conn


# API 1: Search Movies

@app.get("/movielens/api/movies")
def search_movies(search: str = Query("")):
    """
    Επιστρέφει όλες τις ταινίες που περιέχουν το keyword στον τίτλο τους (case-insensitive).
    """
    # 1. Ελέγχουμε αν το search είναι άδειο (ή περιέχει μόνο κενά/spaces)
    if not search.strip():
        return {
            "status": "success",
            "movies": []
        }

    # Αν υπάρχει κείμενο, προχωράμε κανονικά στη βάση
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Το LIKE στην SQLite κάνει case-insensitive αναζήτηση από προεπιλογή
    query = "SELECT * FROM movies WHERE title LIKE ?"
    cursor.execute(query, ('%' + search + '%',))
    
    # Μετατροπή των αποτελεσμάτων σε λίστα από λεξικά
    movies = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Επιστροφή της απάντησης
    return {
        "status": "success",
        "movies": movies
    }

# API 2: Get Ratings for a Movie

@app.get("/movielens/api/ratings/{movieId}")
def get_movie_ratings(movieId: int):
    """
    Επιστρέφει όλες τις κριτικές για τη συγκεκριμένη ταινία.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Επιλέγουμε τα ratings που αντιστοιχούν στο movieId που μας έδωσε ο χρήστης
    query = "SELECT * FROM ratings WHERE movieId = ?"
    cursor.execute(query, (movieId,))
    
    # Μετατροπή σε λίστα από λεξικά
    ratings = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Επιστροφή της απάντησης στη σωστή μορφή
    return {
        "status": "success",
        "ratings": ratings
    }
# Ορίζουμε τη δομή των δεδομένων που περιμένουμε να λάβουμε
class MovieCreate(BaseModel):
    title: str
    genres: str
class RatingInput(BaseModel):
    movieId: int
    rating: float

class RecommendationRequest(BaseModel):
    ratings: List[RatingInput]

#prostheto
class TagSearchRequest(BaseModel):
    search: str

@app.post("/movielens/api/tags/movies")
def search_movies_by_tag(request: TagSearchRequest):
    """
    Επιστρέφει ταινίες βάσει tag. 
    POST request 
    <5 χαρακτήρες: ακριβές ταίριασμα
    >=5 χαρακτήρες: ταίριασμα στους πρώτους 5
    Case-insensitive.
    """
    keyword = request.search.strip()
    if not keyword:
        return {"status": "success", "movies": []}

    conn = get_db_connection()
    cursor = conn.cursor()

    if len(keyword) < 5:
        # Ακριβής ισότητα (case-insensitive)
        query = """
            SELECT m.movieId, m.title, m.genres, t.tag AS matchingTag
            FROM movies m
            JOIN tags t ON m.movieId = t.movieId
            WHERE LOWER(t.tag) = ?
            GROUP BY m.movieId
        """
        cursor.execute(query, (keyword.lower(),))
    else:
        # Ταίριασμα στους πρώτους 5 χαρακτήρες (case-insensitive)
        prefix = keyword[:5].lower()
        query = """
            SELECT m.movieId, m.title, m.genres, t.tag AS matchingTag
            FROM movies m
            JOIN tags t ON m.movieId = t.movieId
            WHERE LOWER(SUBSTR(t.tag, 1, 5)) = ?
            GROUP BY m.movieId
        """
        cursor.execute(query, (prefix,))

    movies = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {
        "status": "success",
        "movies": movies
    }
# ----------


# API 3: Add a New Movie

@app.post("/movielens/api/movies")
def add_movie(movie: MovieCreate):
    """
    Προσθέτει μια νέα ταινία στη βάση δεδομένων και επιστρέφει το νέο ID.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Βρίσκουμε το μεγαλύτερο υπάρχον movieId για να φτιάξουμε ένα νέο μοναδικό ID
    cursor.execute("SELECT MAX(movieId) FROM movies")
    max_id_row = cursor.fetchone()
    # Αν η βάση ήταν άδεια, ξεκινάμε από το 1, αλλιώς προσθέτουμε 1 στο μέγιστο
    new_id = (max_id_row[0] or 0) + 1 
    
    # Εισαγωγή της νέας ταινίας
    query = "INSERT INTO movies (movieId, title, genres) VALUES (?, ?, ?)"
    cursor.execute(query, (new_id, movie.title, movie.genres))
    
    # Αποθήκευση των αλλαγών στη βάση
    conn.commit()
    conn.close()
    
    # Επιστροφή της απάντησης όπως ζητάει η εκφώνηση
    return {
        "status": "success",
        "movieId": new_id
    }

# API 4: Get Recommendations

@app.post("/movielens/api/recommendations")
def get_recommendations(request: RecommendationRequest):
    """
    Επιστρέφει συστάσεις ταινιών με βάση τις κριτικές του χρήστη.
    """
    # Παίρνουμε τις κριτικές του web χρήστη (u)
    user_u_ratings = {r.movieId: r.rating for r in request.ratings}
    
    if not user_u_ratings:
        return {"status": "success", "recommendations": []}

    # Μέση βαθμολογία του χρήστη u
    mean_u = sum(user_u_ratings.values()) / len(user_u_ratings)

    conn = get_db_connection()
    
    # 1. Φέρνουμε όλες τις κριτικές και τις ταινίες από τη βάση με pandas
    ratings_df = pd.read_sql_query("SELECT * FROM ratings", conn)
    movies_df = pd.read_sql_query("SELECT * FROM movies", conn)
    conn.close()

    # 2. Βρίσκουμε χρήστες (v) που έχουν βαθμολογήσει τις ίδιες ταινίες
    # Κρατάμε μόνο τα ratings που αφορούν ταινίες που είδε ο u
    overlapping_ratings = ratings_df[ratings_df['movieId'].isin(user_u_ratings.keys())]
    
    similarities = {}
    
    # Ομαδοποίηση ανά χρήστη v για να υπολογίσουμε το Pearson
    for v_id, v_data in overlapping_ratings.groupby('userId'):
        v_ratings = dict(zip(v_data['movieId'], v_data['rating']))
        
        # Βρίσκουμε τα κοινά movieId
        corated = set(user_u_ratings.keys()).intersection(set(v_ratings.keys()))
        if len(corated) < 2: # Χρειαζόμαστε τουλάχιστον 2 κοινές ταινίες για συσχέτιση
            continue
            
        mean_v = sum(v_ratings.values()) / len(v_ratings)
        
        # Υπολογισμός Pearson Correlation sim(u,v)
        num = sum((user_u_ratings[i] - mean_u) * (v_ratings[i] - mean_v) for i in corated)
        den_u = math.sqrt(sum((user_u_ratings[i] - mean_u)**2 for i in corated))
        den_v = math.sqrt(sum((v_ratings[i] - mean_v)**2 for i in corated))
        
        if den_u == 0 or den_v == 0:
            continue
            
        sim = num / (den_u * den_v)
        if sim > 0: # Κρατάμε μόνο θετική συσχέτιση
            similarities[v_id] = sim

    # 3. Επιλογή top-K πιο όμοιων χρηστών (εδώ K=50) 
    top_k_users = sorted(similarities.items(), key=lambda x: x[1], reverse=True)[:50]
    top_k_user_ids = [u for u, _ in top_k_users]
    
    if not top_k_user_ids:
        return {"status": "success", "recommendations": []}

    # 4. Πρόβλεψη βαθμολογίας για υποψήφιες ταινίες 
    candidates_df = ratings_df[
        (ratings_df['userId'].isin(top_k_user_ids)) & 
        (~ratings_df['movieId'].isin(user_u_ratings.keys())) # Όχι ταινίες που είδε ήδη
    ]
    
    predictions = []
    
    for movie_i, movie_data in candidates_df.groupby('movieId'):
        num_pred = 0
        den_pred = 0
        
        for _, row in movie_data.iterrows():
            v = row['userId']
            if v in similarities:
                sim_uv = similarities[v]
                r_vi = row['rating']
                
                # Υπολογισμός μέσης βαθμολογίας του χρήστη v
                all_v_ratings = ratings_df[ratings_df['userId'] == v]['rating']
                mean_v = all_v_ratings.mean()
                
                num_pred += sim_uv * (r_vi - mean_v)
                den_pred += abs(sim_uv)
                
        if den_pred > 0:
            # Εφαρμογή του πλήρους τύπου
            pred_rating = mean_u + (num_pred / den_pred)
            
            # Κρατάμε λογικά όρια βαθμολογίας 0.5 - 5.0
            pred_rating = max(0.5, min(5.0, pred_rating))
            predictions.append((movie_i, pred_rating))

    # 5. Επιλογή top-N ταινιών (έστω N=10)
    predictions.sort(key=lambda x: x[1], reverse=True)
    top_n = predictions[:10]
    
    # Ετοιμάζουμε την τελική απάντηση (JSON)
    recommendations_result = []
    for movie_id, pred_rating in top_n:
        movie_info = movies_df[movies_df['movieId'] == movie_id].iloc[0]
        recommendations_result.append({
            "movieId": int(movie_id),
            "title": movie_info['title'],
            "genres": movie_info['genres'],
            "predictedRating": round(pred_rating, 2)
        })

    return {
        "status": "success",
        "recommendations": recommendations_result
    }