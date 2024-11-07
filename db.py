import sqlite3
from datetime import datetime, timedelta
from fastapi import HTTPException

from log import logger


# --- Database setup ---
DATABASE_URL = "gifs.db"

# Create database and table if it doesn't exist
def init_db():
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gifs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            author TEXT,
            qr TIMESTAMP DEFAULT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert a placeholder GIF for initial setup if table is empty
    cursor.execute("SELECT COUNT(*) FROM gifs")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO gifs (url, author, qr) VALUES ('', 'system', CURRENT_TIMESTAMP)")
        cursor.execute("INSERT INTO gifs (url, author) VALUES ('https://media.giphy.com/media/xT9IgG50Fb7Mi0prBC/giphy.gif', 'system')")
        cursor.execute("INSERT INTO gifs (url, author) VALUES ('https://media3.giphy.com/media/bbshzgyFQDqPHXBo4c/giphy.gif', 'system')")

    # Create a table to store the timestamp of the latest review
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_meta (
            id INTEGER PRIMARY KEY,
            user_ratings_total INTEGER DEFAULT 0
        )
    """)
    # Insert an initial entry if table is empty
    cursor.execute("SELECT COUNT(*) FROM review_meta")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO review_meta (user_ratings_total) VALUES (0)")
    
    conn.commit()
    conn.close()

def refresh_fetch_current_gifs():
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Calculate the timestamp threshold (10 minutes ago)
    threshold_time = datetime.utcnow() - timedelta(minutes=2)
    threshold_str = threshold_time.strftime('%Y-%m-%d %H:%M:%S')
    logger.debug(f'Threshold time: {threshold_str}')

    # Reset 'qr' field for any entries older than 10 minutes
    cursor.execute("""
        UPDATE gifs
        SET qr = NULL
        WHERE qr IS NOT NULL AND url != '' AND qr < ?
    """, (threshold_str,))
    # Commit the changes
    conn.commit()
    logger.debug(f"Updated 'qr' field for {cursor.rowcount}")
    
    cursor.execute("SELECT url, author, qr, timestamp FROM gifs")
    gifs = cursor.fetchall()
    conn.close()
    
    logger.debug(f"Gifs: {gifs}")
    return gifs

def qr_replace_oldest():
    # When triggered, replace the oldest GIF with a QR code
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Identify the oldest gif record
    cursor.execute("SELECT id FROM gifs WHERE qr IS NULL ORDER BY timestamp ASC LIMIT 1")
    oldest_gif_id = cursor.fetchone()[0]
    logger.debug(f'oldest_gif_id {oldest_gif_id}')
    # Set QR Code for the oldest GIF
    cursor.execute("UPDATE gifs SET qr = CURRENT_TIMESTAMP WHERE id = ?", (oldest_gif_id,))
    conn.commit()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="No available gif found to replace.")
    
    conn.close()
    return {"status": "QR code set"}

def set_new_gif(new_gif_url):
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Identify the oldest QR record
    cursor.execute("SELECT id FROM gifs WHERE qr IS NOT NULL ORDER BY qr ASC LIMIT 1")
    oldest_qr_id = cursor.fetchone()[0]
    # Update the identified record
    cursor.execute("UPDATE gifs SET url = ?, qr = NULL, timestamp = CURRENT_TIMESTAMP WHERE id = ?", (new_gif_url, oldest_qr_id))
    conn.commit()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="No QR code placeholder found.")
    
    conn.close()
    return {"status": "GIF set"}

def get_user_ratings_total():
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT user_ratings_total FROM review_meta WHERE id = 1")
    total = cursor.fetchone()[0]
    conn.close()
    return total

def update_user_ratings_total(new_total):
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("UPDATE review_meta SET user_ratings_total = ? WHERE id = 1", (new_total,))
    conn.commit()
    conn.close()
