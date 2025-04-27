import os
import requests
from bs4 import BeautifulSoup
import json
from listing_schema import ListingSchema  # Assuming this is the correct import


def save_json_to_file(data, file_path):
    """Save JSON data to a file."""
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"JSON data saved to {file_path}")


def fetch_systemkameraer_list(base_url, page_number=1):
    """Fetch the list of system cameras and save it as a JSON file."""
    while True:
        try:
            url = f"{base_url}&page={page_number}"
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
                fetch_and_save_listing_json(url)

            # Check for the "next" page link
            next_page = soup.find('a', rel='next', href=True)
            if not next_page:
                break  # No more pages

            page_number += 1

        except requests.RequestException as e:
            print(f"Error fetching data: {e}")
            break


def fetch_and_save_listing_json(url):
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
                json_text = script.string.split(
                    '= JSON.parse("', 1)[1].rsplit('");', 1)[0]
                json_text = json_text.replace('\\"', '"')

                # Load JSON data
                data = json.loads(json_text)

                # Extract finn_id from the URL
                finn_id = url.split('/')[-1]
                data['finn_id'] = finn_id

                # Parse the JSON data using ListingSchema
                schema = ListingSchema(data)
                parsed_data = schema.extract_all()

                # Determine the file path based on the breadcrumb
                breadcrumb_path = os.path.join(
                    "json_data", "torget", "elektronikk_og_hvitevarer", "foto_og_video", "systemkamera")
                file_path = os.path.join(breadcrumb_path, f"{finn_id}.json")

                # Save the parsed JSON data
                save_json_to_file(parsed_data, file_path)
                break

    except requests.RequestException as e:
        print(f"Error fetching listing data: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {url}: {e}")


def extract_urls(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    urls = []

    # Find all <a> tags with class 'sf-search-ad-link' and extract the href attribute
    for a_tag in soup.find_all('a', class_='sf-search-ad-link', href=True):
        urls.append(a_tag['href'])

    return urls


def save_urls_to_json(urls, page_number):
    """Save page URLs to a JSON file in the breadcrumb path."""
    breadcrumb_path = os.path.join(
        "json_data", "torget", "elektronikk_og_hvitevarer", "foto_og_video", "systemkamera", "pages")
    file_path = os.path.join(breadcrumb_path, f"page_{page_number}_urls.json")

    save_json_to_file(urls, file_path)


def main():
    # Base URL for the systemkameraer category
    base_url = 'https://www.finn.no/recommerce/forsale/search?product_category=2.93.3904.66'
    print("Fetching systemkameraer listings...")
    fetch_systemkameraer_list(base_url)


if __name__ == "__main__":
    main()
