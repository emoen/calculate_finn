import os
import json
import sqlite3
from datetime import datetime


def create_database(db_name='listings.db'):
    """Create a SQLite database and tables for storing listings and processed folders."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id TEXT PRIMARY KEY,
            data TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_folders (
            folder_name TEXT PRIMARY KEY,
            done BOOLEAN DEFAULT FALSE
        )
    ''')
    conn.commit()
    return conn


def load_existing_finn_ids(conn):
    """Load existing finn_ids from the database into a set."""
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM listings')
    existing_ids = {row[0] for row in cursor.fetchall()}
    return existing_ids


def insert_listing(conn, listing_id, data):
    """Insert a listing into the database."""
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO listings (id, data)
        VALUES (?, ?)
    ''', (listing_id, json.dumps(data)))
    conn.commit()


def mark_folder_as_processed(conn, folder_name):
    """Mark a folder as processed in the database."""
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO processed_folders (folder_name, done)
        VALUES (?, FALSE)
    ''', (folder_name,))
    conn.commit()


def update_folders_to_done(conn):
    """Update all processed folders to done."""
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE processed_folders
        SET done = TRUE
        WHERE done = FALSE
    ''')
    conn.commit()


def is_folder_processed(conn, folder_name):
    """Check if a folder has already been processed."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 1 FROM processed_folders WHERE folder_name = ?
    ''', (folder_name,))
    return cursor.fetchone() is not None


def process_json_files(directory):
    """Process all JSON files in the given directory and insert them into the database."""
    conn = create_database()
    existing_ids = load_existing_finn_ids(conn)
    folder_name = os.path.basename(directory)

    if is_folder_processed(conn, folder_name):
        print(f"Folder {folder_name} has already been processed.")
        conn.close()
        return

    for root, _, files in os.walk(directory):
        # Skip directories named 'pages'
        if 'pages' in root.split(os.sep):
            continue

        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    # Debugging: Print the type of data
                    print(f"Processing {file_path}: {type(data)}")

                    if isinstance(data, dict):
                        # Handle dictionary data
                        listing_id = data.get(
                            'finn_id', os.path.splitext(file)[0])
                        if listing_id not in existing_ids:
                            insert_listing(conn, listing_id, data)
                            existing_ids.add(listing_id)
                        else:
                            print(f"Listing {listing_id} already processed.")

                    else:
                        print(f"Unexpected data format in {file_path}")

    mark_folder_as_processed(conn, folder_name)
    conn.close()


def store_new_json_files_in_db():
    """Store new JSON files in the database."""
    # Directory for today's listings
    base_directory = 'json_data'
    today = datetime.now().strftime('%d%m%Y')
    directories = [d for d in os.listdir(
        base_directory) if d.startswith('torget_')]

    conn = create_database()
    # Update folders to done at the start of a new day
    update_folders_to_done(conn)

    for directory in directories:
        full_path = os.path.join(base_directory, directory)
        print(f"Processing JSON files in {full_path}...")
        process_json_files(full_path)

    conn.close()


if __name__ == "__main__":
    store_new_json_files_in_db()
