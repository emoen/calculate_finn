import os
import requests
from bs4 import BeautifulSoup
import json
from listing_schema import ListingSchema  # Assuming this is the correct import
from datetime import datetime


def save_json_to_file(data, file_path):
    """Save JSON data to a file."""
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"JSON data saved to {file_path}")


def fetch_items_on_page(base_url, existing_ids, error_count=0, index_of_solgt=0, page_number=1):
    """Fetch the list of system cameras and save it as a JSON file."""
    consecutive_existing_count = 0

    while True:
        try:
            print(f"**** page {page_number} ****")

            url = f"{base_url}?page={page_number}"
            response = requests.get(url)
            response.raise_for_status()

            # Use BeautifulSoup to parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract URLs from <a> tags with class 'sf-search-ad-link'
            urls = extract_urls(response.text)

            # Filter out URLs containing 'ad.html'
            filtered_urls = [url for url in urls if 'ad.html' not in url]
            save_urls_to_json(filtered_urls, page_number)

            # Fetch and save JSON data for each URL
            for url in filtered_urls:
                finn_id = url.split('/')[-1]
                if finn_id in existing_ids:
                    consecutive_existing_count += 1
                    if consecutive_existing_count >= 3:
                        print("Reached 3 consecutive existing finn_ids. Stopping.")
                        return error_count, index_of_solgt
                    continue
                else:
                    consecutive_existing_count = 0

                error_count, index_of_solgt = fetch_and_save_item(
                    url, error_count, index_of_solgt)

            # Check for the "next" page link
            next_page = soup.find('a', rel='next', href=True)
            if not next_page:
                print(f"**** Finished. Num pages read: {page_number} ****")
                print(f"Total number of items with errors: {error_count}")
                break  # No more pages

            page_number += 1

        except requests.RequestException as e:
            print(f"Error fetching data: {e}")
            print(f"Total number of items with errors: {error_count}")
            break

    return error_count, index_of_solgt


def fetch_and_save_item(url, error_count, index_of_solgt):
    """Fetch JSON data for a listing and save it in the appropriate directory."""
    try:
        response = requests.get(url)
        response.raise_for_status()

        # Use BeautifulSoup to parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the script tag containing the JSON data
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string and '{' in script.string and '}' in script.string:
                # Extract JSON data from the script tag
                try:
                    json_texts = script.string.split(
                        '= JSON.parse("', 1)[1].rsplit('");', 1)
                    json_text = json_texts[0]
                    single_escaped_json = json_text.replace('\\\\', '\\')
                    proper_json = single_escaped_json.replace('\\"', '"')

                    data = json.loads(proper_json)

                    # Parse the JSON data using ListingSchema
                    schema = ListingSchema(data)
                    parsed_data = schema.extract_all()
                    # Extract finn_id from the URL
                    finn_id = url.split('/')[-1]
                    parsed_data['finn_id'] = finn_id

                    # Extract breadcrumb for directory structure
                    breadcrumb = extract_breadcrumb(soup)
                    breadcrumb_path = os.path.join(
                        "json_data", f"torget_{datetime.now().strftime('%d%m%Y')}", *breadcrumb, finn_id)

                    # Save the parsed JSON data
                    json_file_path = os.path.join(
                        breadcrumb_path, f"{finn_id}.json")
                    save_json_to_file(parsed_data, json_file_path)

                    # Download images
                    download_images(parsed_data.get(
                        'images', []), breadcrumb_path)
                except IndexError as e:
                    log_solgt_url(url, index_of_solgt, str(e))
                    index_of_solgt += 1
                break

    except requests.RequestException as e:
        print(f"Error fetching listing data: {e}")
        error_count += 1
    except json.JSONDecodeError as e:
        error_message = f"Error decoding JSON from {url}: {e}"
        print(error_message)
        log_error(breadcrumb_path, error_message)
        error_count += 1

    return error_count, index_of_solgt


def log_error(directory, message):
    """Log an error message to a file in the specified directory."""
    if not os.path.exists(directory):
        os.makedirs(directory)

    error_file_path = os.path.join(directory, "errors.log")
    with open(error_file_path, 'a', encoding='utf-8') as error_file:
        error_file.write(message + "\n")


def download_images(images, directory):
    """Download images and save them in the specified directory."""
    if not os.path.exists(directory):
        os.makedirs(directory)

    for image in images:
        image_url = image['uri']
        image_name = os.path.basename(image_url)
        if not os.path.splitext(image_name)[1]:
            image_name += '.jpg'

        image_path = os.path.join(directory, image_name)

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
    breadcrumb_div = soup.find('div', class_='flex space-x-8')
    if breadcrumb_div:
        for a_tag in breadcrumb_div.find_all('a', class_='s-text-link'):
            tag_content = a_tag.contents[0]
            breadcrumb.append(tag_content.strip())
    return breadcrumb


def extract_urls(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    urls = []

    # Find all <a> tags with class 'sf-search-ad-link' and extract the href attribute
    for a_tag in soup.find_all('a', class_='sf-search-ad-link', href=True):
        urls.append(a_tag['href'])

    return urls


def save_urls_to_json(urls, page_number):
    """Save page URLs to a JSON file in the breadcrumb path, under pages/"""
    breadcrumb_path = os.path.join(
        "json_data", f"torget_{datetime.now().strftime('%d%m%Y')}", "pages")
    file_path = os.path.join(breadcrumb_path, f"page_{page_number}_urls.json")

    save_json_to_file(urls, file_path)


def log_solgt_url(url, index, error_message):
    """Log the URL to solgt.txt and create a numbered error log in the specified directory."""
    today = datetime.now().strftime('%d%m%Y')
    solgt_directory = os.path.join("json_data", f"torget_{today}", "solgt")
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


def main():
    # Base URL for the systemkameraer category
    base_url = 'https://www.finn.no/recommerce/forsale/search'
    print("Fetching all items...")
    fetch_items_on_page(base_url)


if __name__ == "__main__":
    main()
