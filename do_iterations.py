import os
import sqlite3
from datetime import datetime
from track_new import fetch_items_on_page  # Import the function directly
from populate_database_new import store_new_json_files_in_db  # Import the new function


def load_existing_finn_ids(db_name='listings.db'):
    """Load existing finn_ids from the database into a set."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM listings')
    existing_ids = {row[0] for row in cursor.fetchall()}
    conn.close()
    return existing_ids


def main():
    existing_ids = load_existing_finn_ids()
    print(f"Loaded {len(existing_ids)} existing finn_ids.")

    # Base URL for the systemkameraer category
    base_url = 'https://www.finn.no/recommerce/forsale/search'

    # Fetch items, passing the existing_ids set
    fetch_items_on_page(base_url, existing_ids)

    # Store new JSON files in the database
    store_new_json_files_in_db()

    print("Finished processing new listings.")


if __name__ == "__main__":
    main()
