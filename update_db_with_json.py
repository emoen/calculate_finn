import os
import json
import sqlite3
from datetime import datetime


def create_database_connection(db_name='listings.db'):
    """Create a connection to the SQLite database."""
    conn = sqlite3.connect(db_name)
    return conn


def insert_listing(conn, listing_id, data):
    """Insert a listing into the database with the current timestamp."""
    cursor = conn.cursor()
    current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        INSERT OR REPLACE INTO listings (id, data, inserted_at)
        VALUES (?, ?, ?)
    ''', (listing_id, json.dumps(data), current_timestamp))
    conn.commit()


def process_json_files(base_directory):
    """Process all JSON files in the given directory and insert them into the database."""
    conn = create_database_connection()

    for root, dirs, files in os.walk(base_directory):
        # Check if the directory is a 'torget_<date>' directory
        if os.path.basename(root).startswith('torget_'):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                        # Extract finn_id from the file name or data
                        listing_id = data.get(
                            'finn_id', os.path.splitext(file)[0])

                        # Insert the listing into the database
                        insert_listing(conn, listing_id, data)

            # Log completion of processing for the current directory
            print(f"Completed processing directory: {root}")

    conn.close()


def main():
    base_directory = 'json_data'
    process_json_files(base_directory)
    print("All JSON files have been processed and inserted into the database.")


if __name__ == "__main__":
    main()
