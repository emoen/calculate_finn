import os
import sqlite3
import time
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


def download_items():
    # Simulate the download process
    print("Starting downloads...")
    time.sleep(5)  # Simulate time taken for downloads
    print("Downloads completed.")


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

        existing_ids = load_existing_finn_ids()
        print(f"Loaded {len(existing_ids)} existing finn_ids.")

        # Base URL for the systemkameraer category
        base_url = 'https://www.finn.no/recommerce/forsale/search'

        # Fetch items, passing the existing_ids set and current counts
        error_count, index_of_solgt = fetch_items_on_page(
            base_url, existing_ids, error_count, index_of_solgt)

        # Store new JSON files in the database
        store_new_json_files_in_db()

        print("Finished processing new listings.")

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
