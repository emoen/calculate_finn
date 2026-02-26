import os
import requests
from bs4 import BeautifulSoup
import json
import argparse
from datetime import datetime
from src.config import BASE_DIR, JSON_DATA_DIR

# Use configuration from src.config
# BASE_DIR is already imported

def save_json_to_file(data, file_path):
    """Save JSON data to a file."""
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"JSON data saved to {file_path}")


def extract_finn_id(url):
    """Extract normalized numeric FINN ID from URL."""
    if not url:
        return None

    cleaned = url.split('?', 1)[0].split('#', 1)[0].rstrip('/')
    finn_id = cleaned.split('/')[-1]
    if finn_id.endswith('.html'):
        finn_id = finn_id[:-5]

    return finn_id if finn_id.isdigit() else None


def finn_id_exists_anywhere(finn_id):
    """Check if a FINN ID directory already exists in any cars_DATE folder."""
    for date_dir in JSON_DATA_DIR.glob("cars_*"):
        if (date_dir / finn_id).is_dir():
            return True
    return False


def fetch_items_on_page(base_url, existing_ids, error_count=0, index_of_solgt=0, page_number=1, limit=None):
    """Fetch the list of cars and save it as a JSON file."""
    consecutive_existing_count = 0
    new_cars_fetched = 0
    seen_page_signatures = set()
    consecutive_no_new_pages = 0
    max_consecutive_no_new_pages = 3

    while True:
        try:
            if limit and new_cars_fetched >= limit:
                print(f"Limit of {limit} new cars reached. Stopping.")
                return error_count, index_of_solgt

            print(f"**** page {page_number} ****")

            if '?' in base_url:
                url = f"{base_url}&page={page_number}"
            else:
                url = f"{base_url}?page={page_number}"
            
            response = requests.get(url)
            response.raise_for_status()

            # Use BeautifulSoup to parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract URLs
            urls = extract_urls(response.text)

            # Filter out URLs containing 'ad.html' just in case
            filtered_urls = [url for url in urls if 'ad.html' not in url]
            save_urls_to_json(filtered_urls, page_number)

            if not filtered_urls:
                print("No URLs found on this page.")
                if page_number > 1:
                    print(f"**** Finished. Num pages read: {page_number} ****")
                    break
                # Only strictly break if no items and usually that means end of results.

            page_finn_ids = tuple(sorted({finn_id for item_url in filtered_urls if (finn_id := extract_finn_id(item_url))}))
            if not page_finn_ids:
                print(f"No valid FINN IDs found on page {page_number}. Stopping.")
                break

            if page_finn_ids in seen_page_signatures:
                print(f"Page {page_number} repeats previously seen listings. Stopping pagination.")
                break

            seen_page_signatures.add(page_finn_ids)

            new_saved_on_page = 0

            # Fetch and save JSON data for each URL
            for url in filtered_urls:
                # Cars URL: https://www.finn.no/mobility/item/366152300
                # Extract ID.
                finn_id = extract_finn_id(url)
                if not finn_id:
                    print(f"Could not parse ID from {url}")
                    continue

                if finn_id in existing_ids or finn_id_exists_anywhere(finn_id):
                    existing_ids.add(finn_id)
                    consecutive_existing_count += 1
                    if consecutive_existing_count % 50 == 0:
                        print(f"Skipped {consecutive_existing_count} existing cars...")
                    # if consecutive_existing_count >= 10: 
                    #     print("Reached 10 consecutive existing finn_ids. Stopping.")
                    #     return error_count, index_of_solgt
                    continue
                else:
                    consecutive_existing_count = 0

                error_count, index_of_solgt, saved = fetch_and_save_item(
                    url, finn_id, error_count, index_of_solgt)

                if saved:
                    existing_ids.add(finn_id)
                    new_cars_fetched += 1
                    new_saved_on_page += 1
                if limit and new_cars_fetched >= limit:
                    print(f"Limit of {limit} new cars reached. Stopping.")
                    return error_count, index_of_solgt

            if new_saved_on_page == 0:
                consecutive_no_new_pages += 1
                print(
                    f"No new cars saved on page {page_number} "
                    f"({consecutive_no_new_pages}/{max_consecutive_no_new_pages} consecutive)."
                )
                if consecutive_no_new_pages >= max_consecutive_no_new_pages:
                    print("Reached consecutive no-new-pages threshold. Stopping pagination.")
                    break
            else:
                consecutive_no_new_pages = 0

            # 'next' link can be unreliable on FINN; use it only for logging
            next_page = soup.find('a', rel='next', href=True)
            if not next_page:
                print(f"Note: 'Next' link not found on page {page_number}. Continuing with page increment.")
            
            page_number += 1
            
            # Simple rate limiting
            import time
            time.sleep(1)

        except requests.RequestException as e:
            print(f"Error fetching data: {e}")
            print(f"Total number of items with errors: {error_count}")
            break

    return error_count, index_of_solgt


def fetch_and_save_item(url, finn_id, error_count, index_of_solgt):
    """Fetch JSON data for a listing and save it in the appropriate directory."""
    if finn_id_exists_anywhere(finn_id):
        return error_count, index_of_solgt, False

    try:
        response = requests.get(url)
        response.raise_for_status()

        # Use BeautifulSoup to parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the script tag containing the JSON data (Schema.org)
        # We look for application/ld+json
        script_tags = soup.find_all('script', type='application/ld+json')
        data = None
        
        for script in script_tags:
            if script.string:
                try:
                    loaded = json.loads(script.string)
                    # Often it's a list of schemas or a single dict
                    if isinstance(loaded, list):
                        for item in loaded:
                            if item.get('@type') in ['Product', 'Vehicle', 'Car', 'MotorCycle']:
                                data = item
                                break
                    elif isinstance(loaded, dict):
                         if loaded.get('@type') in ['Product', 'Vehicle', 'Car', 'MotorCycle']:
                            data = loaded
                    
                    if data:
                        break
                except json.JSONDecodeError:
                    continue
        
        if data:
            # Add finn_id explicitly if missing
            if 'finn_id' not in data:
                data['finn_id'] = finn_id

            # --- Extract Description from HTML ---
            # JSON-LD description is often empty or missing. We fallback/overwrite with HTML content.
            desc_div = soup.find('div', class_='import-decoration')
            if desc_div:
                # Get text with newlines preserved
                full_description = desc_div.get_text(separator='\n', strip=True)
                if full_description:
                    data['description'] = full_description
            # -------------------------------------
            
            # Directory: cars/data_json/cars_DATE/finn_id...
            today_str = datetime.now().strftime('%d%m%Y')
            
            # Build path
            breadcrumb_path = JSON_DATA_DIR / f"cars_{today_str}" / finn_id

            # Save the parsed JSON data
            json_file_path = os.path.join(breadcrumb_path, f"{finn_id}.json")
            save_json_to_file(data, json_file_path)

            # Download images if present in Schema.org
            # Schema.org image can be list of strings or single string
            images = data.get('image')
            if images:
                if isinstance(images, str):
                    images = [images]
                download_images(images, breadcrumb_path)
            return error_count, index_of_solgt, True
        else:
            # Could not find data
            log_solgt_url(url, index_of_solgt, "No JSON-LD data found")
            index_of_solgt += 1

    except requests.RequestException as e:
        print(f"Error fetching listing data: {e}")
        error_count += 1
    except json.JSONDecodeError as e:
        error_message = f"Error decoding JSON from {url}: {e}"
        print(error_message)
        error_count += 1
    except Exception as e:
        print(f"Unexpected error for {url}: {e}")
        error_count += 1

    return error_count, index_of_solgt, False


def log_error(directory, message):
    """Log an error message to a file in the specified directory."""
    if not os.path.exists(directory):
        os.makedirs(directory)

    error_file_path = os.path.join(directory, "errors.log")
    with open(error_file_path, 'a', encoding='utf-8') as error_file:
        error_file.write(message + "\n")


def download_images(image_urls, directory):
    """Download images and save them in the specified directory."""
    if not os.path.exists(directory):
        os.makedirs(directory)

    for i, image_url in enumerate(image_urls):
        # image_url might be a simple string
        if not isinstance(image_url, str):
            continue
            
        # Clean URL?
        
        image_name = f"image_{i}.jpg" # Simple naming or keep original
        # Try to keep original name if possible
        base_name = os.path.basename(image_url)
        if len(base_name) > 5 and '.' in base_name:
             image_name = base_name.split('?')[0] # remove query params

        image_path = os.path.join(directory, image_name)
        
        # Don't download if exists
        if os.path.exists(image_path):
            continue

        try:
            img_response = requests.get(image_url)
            img_response.raise_for_status()

            with open(image_path, 'wb') as img_file:
                img_file.write(img_response.content)
            print(f"Image saved to {image_path}")

        except requests.RequestException as e:
            print(f"Error downloading image {image_url}: {e}")


def extract_breadcrumb(soup):
    """Extract breadcrumb from the HTML soup."""
    breadcrumb = []
    # Try different breadcrumb structures
    # Structure 1: div class="flex space-x-8" (recommerce)
    # Structure 2: nav aria-label="Breadcrumb" -> ol -> li -> a
    
    # Try generic 'nav' with 'breadcrumbs' in class or aria-label
    nav = soup.find('nav', attrs={'aria-label': 'Breadcrumb'})
    if not nav:
         nav = soup.find('nav', class_='breadcrumbs')
    
    if nav:
        for a_tag in nav.find_all('a'):
            if a_tag.text:
                breadcrumb.append(sanitize_filename(a_tag.text.strip()))
    else:
        # Fallback to similar looking divs if relevant
        breadcrumb_div = soup.find('div', class_='flex space-x-8')
        if breadcrumb_div:
            for a_tag in breadcrumb_div.find_all('a', class_='s-text-link'):
                tag_content = a_tag.contents[0] if a_tag.contents else ""
                breadcrumb.append(sanitize_filename(str(tag_content).strip()))
    
    return breadcrumb

def sanitize_filename(name):
    return "".join([c for c in name if c.isalpha() or c.isdigit() or c==' ' or c=='_']).rstrip().replace(' ', '_')

def extract_urls(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    urls = []

    # Finn cars usually:
    # <article class="ads__unit"> ... <a href="/mobility/item/..." class="ads__unit__link">
    # Search for all 'a' tags that contain /mobility/item/ or /car/
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        # Check against expected patterns
        if '/mobility/item/' in href or '/car/item/' in href:
             # Ensure absolute URL
            if href.startswith('/'):
                href = f"https://www.finn.no{href}"
            
            if href not in urls:
                urls.append(href)
                
    return urls


def save_urls_to_json(urls, page_number):
    """Save page URLs to a JSON file in the breadcrumb path, under pages/"""
    breadcrumb_path = JSON_DATA_DIR / f"cars_{datetime.now().strftime('%d%m%Y')}" / "pages"
    os.makedirs(breadcrumb_path, exist_ok=True)
    file_path = breadcrumb_path / f"page_{page_number}_urls.json"
    save_json_to_file(urls, str(file_path))


def log_solgt_url(url, index, error_message):
    """Log the URL to solgt.txt and create a numbered error log in the specified directory."""
    today = datetime.now().strftime('%d%m%Y')
    solgt_directory = JSON_DATA_DIR / f"cars_{today}" / "solgt"
    if not os.path.exists(solgt_directory):
        os.makedirs(solgt_directory)

    # Log the URL to solgt.txt
    solgt_file_path = os.path.join(solgt_directory, "solgt.txt")
    with open(solgt_file_path, 'a', encoding='utf-8') as solgt_file:
        solgt_file.write(url + "\n")

    # Log the error message to a numbered error log
    error_log_path = os.path.join(solgt_directory, f"{index}_error.log")
    with open(error_log_path, 'w', encoding='utf-8') as error_log_file:
        error_log_file.write(error_message + "\n")


def get_downloaded_ids():
    """Scan json_data directory for already downloaded car IDs."""
    existing_ids = set()
    
    if not os.path.exists(JSON_DATA_DIR):
        return existing_ids

    # Walk through all date directories (e.g., cars_20012026)
    for date_dir in os.listdir(JSON_DATA_DIR):
        date_path = os.path.join(JSON_DATA_DIR, date_dir)
        if os.path.isdir(date_path) and date_dir.startswith("cars_"):
            # Simplified: Assume IDs are immediate subdirectories of cars_DATE
            for item in os.listdir(date_path):
                if item.isdigit():
                    existing_ids.add(item)
    
    print(f"Found {len(existing_ids)} existing car IDs.")
    return existing_ids


def main():
    parser = argparse.ArgumentParser(description="Fetch car listings from Finn.no")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of new cars to fetch")
    args = parser.parse_args()

    # Base URL for cars
    base_url = 'https://www.finn.no/mobility/search/car?registration_class=1'
    print("Fetching all car items...")
    if args.limit:
        print(f"Limiting to {args.limit} new items.")
    
    existing_ids = get_downloaded_ids()
    fetch_items_on_page(base_url, existing_ids, limit=args.limit)


if __name__ == "__main__":
    main()
