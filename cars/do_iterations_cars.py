import os
import sqlite3
import time
from datetime import datetime

# Local imports - adjusting for new structure where we run this as a module or with PYTHONPATH set
try:
    from src.scraping.track_cars import fetch_items_on_page
    from src.processing.populate_database_cars import store_new_json_files_in_db
except ImportError:
    # Fallback to local import if strictly in the same package (unlikely here) or direct execution
    try:
        from track_cars import fetch_items_on_page
        from populate_database_cars import store_new_json_files_in_db
    except ImportError:
        # If we are running from cars root like python3 src/scraping/do_iterations_cars.py
        import sys
        # Add src/scraping and src/processing to path? No, better to add root of project.
        # Assuming current dir is cars/ and we want to import relative to src.
        # But moving forward, let's assume we run with python -m src.scraping.do_iterations_cars
        print("Import Error: best run as 'python3 -m src.scraping.do_iterations_cars' from cars/ folder")
        raise

# Define base directory relative to this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_existing_finn_ids(db_name='listings.db'):
    """Load existing finn_ids from the database into a set."""
    # Ensure db_name is relative to BASE_DIR
    if not os.path.isabs(db_name):
        db_path = os.path.join(BASE_DIR, db_name)
    else:
        db_path = db_name

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Ensure table exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id TEXT PRIMARY KEY,
            data TEXT,
            inserted_at TIMESTAMP
        )
    ''')
    cursor.execute('SELECT id FROM listings')
    existing_ids = {row[0] for row in cursor.fetchall()}
    conn.close()
    return existing_ids


def main():
    error_count = 0
    index_of_solgt = 0
    last_processed_date = None

    while True:
        # Step 1: Record the start time
        start_time = datetime.now()

        current_time = datetime.now()
        current_date = current_time.strftime('%d%m%Y')

        # Reset counts if a new day has started
        if last_processed_date != current_date:
            error_count = 0
            index_of_solgt = 0
            last_processed_date = current_date
            print(f"New day detected: {current_date}. Resetting counters.")

        existing_ids = load_existing_finn_ids()
        print(f"Loaded {len(existing_ids)} existing finn_ids.")

        # Base URL for the cars category
        base_url = 'https://www.finn.no/mobility/search/car?registration_class=1'

        # Fetch items, passing the existing_ids set and current counts
        error_count, index_of_solgt = fetch_items_on_page(
            base_url, existing_ids, error_count, index_of_solgt)

        # Store new JSON files in the database
        store_new_json_files_in_db()

        print("Finished processing new car listings.")

        # Step 3: Calculate the elapsed time
        elapsed_time = datetime.now() - start_time
        elapsed_seconds = elapsed_time.total_seconds()

        # Step 4: Determine the current day of the week and hour
        current_day = start_time.weekday()  # Monday is 0 and Sunday is 6
        current_hour = start_time.hour

        # Step 5: Set the wait time based on the day and time
        if 0 <= current_hour < 8 or current_hour == 23:  # Night hours
            max_wait_time = 2700  # 45 minutes in seconds
        elif current_day >= 4:  # Friday (4) to Sunday (6)
            max_wait_time = 1200  # 20 minutes in seconds
        else:
            max_wait_time = 1800  # 30 minutes in seconds

        # Step 6: Calculate the remaining time to wait
        wait_time = max(0, max_wait_time - elapsed_seconds)

        # Step 7: Wait for the remaining time
        print(f"Waiting for {wait_time} seconds before the next iteration.")
        time.sleep(wait_time)


if __name__ == "__main__":
    main()
