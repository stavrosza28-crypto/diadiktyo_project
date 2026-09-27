import os
import sqlite3
import pandas as pd
import requests
import zipfile
from io import BytesIO

DB_NAME = "movielens.db"
DATASET_URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"

def download_and_extract_data():
    """Κατεβάζει το αρχείο zip και το κάνει extract."""
    print("Κατέβασμα του dataset...")
    response = requests.get(DATASET_URL)
    
    # Εξαγωγή του zip στη μνήμη και αποθήκευση στον φάκελο 'dataset'
    with zipfile.ZipFile(BytesIO(response.content)) as z:
        z.extractall("dataset")
    print("Το dataset κατέβηκε και έγινε εξαγωγή στον φάκελο 'dataset/ml-latest-small'.")

def create_database():
    """Διαβάζει τα CSV και τα μεταφέρει στην SQLite βάση."""
    print(f"Δημιουργία και φόρτωση δεδομένων στη βάση '{DB_NAME}'...")
    
    # Σύνδεση με τη βάση (δημιουργείται αυτόματα αν δεν υπάρχει)
    conn = sqlite3.connect(DB_NAME)

    # Διαδρομή προς τα εξαγόμενα CSV αρχεία
    base_path = os.path.join("dataset", "ml-latest-small")

    # Φόρτωση των CSV σε pandas DataFrames
    movies_df = pd.read_csv(os.path.join(base_path, "movies.csv"))
    ratings_df = pd.read_csv(os.path.join(base_path, "ratings.csv"))
    tags_df = pd.read_csv(os.path.join(base_path, "tags.csv"))

    # Αποθήκευση των DataFrames στην SQLite
    # Το if_exists='replace' φροντίζει να αντικατασταθούν οι πίνακες αν το ξανατρέξουμε
    # Το index=False αποτρέπει τη δημιουργία επιπλέον στήλης για το index του DataFrame
    movies_df.to_sql("movies", conn, if_exists="replace", index=False)
    ratings_df.to_sql("ratings", conn, if_exists="replace", index=False)
    tags_df.to_sql("tags", conn, if_exists="replace", index=False)

    conn.close()
    print("Η βάση δεδομένων είναι έτοιμη!")

if __name__ == "__main__":
    # Αν δεν υπάρχει ο φάκελος με τα δεδομένα, τα κατεβάζει
    if not os.path.exists(os.path.join("dataset", "ml-latest-small")):
        download_and_extract_data()
        
    create_database()