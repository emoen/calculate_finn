import os
import sqlite3
import json
from listing_schema import ListingSchema


def create_database():
    conn = sqlite3.connect('finn_listings.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY,
            title TEXT,
            price INTEGER,
            link TEXT,
            category_id INTEGER,
            category_value TEXT,
            category_parent_id INTEGER,
            category_parent_value TEXT,
            description TEXT,
            location_lat REAL,
            location_long REAL,
            condition_id INTEGER,
            condition_value TEXT,
            images TEXT
        )
    ''')
    conn.commit()
    conn.close()


def save_listing(id, title, price, link, category_id, category_value, category_parent_id, category_parent_value, description, location_lat, location_long, condition_id, condition_value, images):
    conn = sqlite3.connect('finn_listings.db')
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO listings (
            id, title, price, link, category_id, category_value, category_parent_id, category_parent_value,
            description, location_lat, location_long, condition_id, condition_value, images
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (id, title, price, link, category_id, category_value, category_parent_id, category_parent_value, description, location_lat, location_long, condition_id, condition_value, images))
    conn.commit()
    conn.close()


def process_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Debug: Print the raw JSON data to understand its structure
    print("Raw JSON Data:", data)

    # Use the ListingSchema class to extract data
    listing = ListingSchema(data)
    extracted_data = listing.extract_all()

    # Debug: Print the extracted data to understand its structure
    print("Extracted Data:", extracted_data)

    # Extract the finn_id and link from the root of the JSON
    finn_id = data.get('finn_id', 'ID not found')
    link = data.get('url', 'URL not found')

    if finn_id == 'ID not found':
        print("Warning: 'finn_id' not found in the JSON data.")
        return

    # Extract additional fields
    item_data = extracted_data['itemData']
    title = item_data.get('title', 'Title not found')
    price = item_data.get('price', 0)
    description = item_data.get('description', 'Description not found')
    location = item_data.get('location', {})
    location_lat = location.get('position', {}).get('lat', 0.0)
    location_long = location.get('position', {}).get('lng', 0.0)
    condition = item_data.get('extras', [{}])[0]
    condition_id = condition.get('id', 0)
    condition_value = condition.get('value', 'Condition not found')
    category = item_data.get('category', {})
    category_id = category.get('id', 0)
    category_value = category.get('value', 'Category not found')
    category_parent = category.get('parent', {})
    category_parent_id = category_parent.get('id', 0)
    category_parent_value = category_parent.get(
        'value', 'Parent category not found')
    images = ', '.join([img.get('uri', '')
                       for img in item_data.get('images', [])])

    print(f"Processing file: {file_path}")

    # Save listing to the database
    save_listing(finn_id, title, price, link, category_id, category_value, category_parent_id,
                 category_parent_value, description, location_lat, location_long, condition_id, condition_value, images)


def main():
    create_database()
    directory = "json_data"
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            file_path = os.path.join(directory, filename)
            process_json_file(file_path)


if __name__ == "__main__":
    main()
