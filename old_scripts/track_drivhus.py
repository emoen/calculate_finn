import os
import requests
from bs4 import BeautifulSoup
import json


def save_json_to_file(data, id, url):
    """Save JSON data to a file with URL and FINN ID."""
    # Add URL and FINN ID to the root of the JSON data
    data['url'] = url
    data['finn_id'] = id

    # Extract category information for directory structure
    category = data.get('loaderData', {}).get(
        'item-recommerce', {}).get('itemData', {}).get('category', {})
    category_value = category.get('value', 'unknown').replace('/', '_')
    category_parent_value = category.get('parent', {}).get(
        'value', 'unknown').replace('/', '_')

    directory = os.path.join("json_data", "torget",
                             category_parent_value, category_value)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Define the file path
    file_path = os.path.join(directory, f"{id}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"JSON data saved to {file_path}")


def fetch_single_listing(url):
    """Fetch a single listing and save it as a JSON file."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract the FINN code from the URL
        finn_code = url.split('/')[-1]

        # Find the script tag containing the JSON data
        script_tag = soup.find(
            'script', string=lambda t: t and 'window.__staticRouterHydrationData' in t)
        if script_tag:
            # Extract JSON data from the script tag
            json_text = script_tag.string.split(
                '= JSON.parse("', 1)[1].rsplit('");', 1)[0]
            json_text = json_text.replace('\\"', '"')

            # Load JSON data
            data = json.loads(json_text)

            # Save JSON data to a file with URL and FINN ID
            save_json_to_file(data, finn_code, url)

    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")


def main():
    # URL for the systemkameraer category
    url = 'https://www.finn.no/recommerce/forsale/item/401373891'
    print("Fetching single listing from Torget...")
    fetch_single_listing(url)


if __name__ == "__main__":
    main()
