import sqlite3
from datetime import datetime


def add_timestamp_to_listings(db_name='listings.db'):
    """Add an inserted_at field to the listings table and update it with the current timestamp."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Add a new column for the timestamp if it doesn't exist
    cursor.execute("PRAGMA table_info(listings)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'inserted_at' not in columns:
        cursor.execute("ALTER TABLE listings ADD COLUMN inserted_at TIMESTAMP")

    # Get the current timestamp
    current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Update all existing records with the current timestamp
    cursor.execute("UPDATE listings SET inserted_at = ?", (current_timestamp,))

    conn.commit()
    conn.close()
    print("Inserted_at field added and updated for all records.")


if __name__ == "__main__":
    add_timestamp_to_listings()
