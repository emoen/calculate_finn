"""
Build static JSON API files from rankings data.

Reads rankings.json + car detail JSONs and produces:
  web/api/meta.json          - pagination metadata & filter options
  web/api/cars/page-1.json   - first page of cars (sorted by score desc)
  web/api/cars/page-2.json   - ...
  web/api/cars/all.json      - lightweight list for client-side search

Each page contains fully hydrated car objects (score, name, price, image, etc.)
so the frontend never needs to make extra requests per car.
"""

import html
import json
import os
import shutil
from pathlib import Path
from src.config import BASE_DIR, JSON_DATA_DIR, RANKINGS_DATA_DIR, WEB_DIR

RANKINGS_FILE = RANKINGS_DATA_DIR / 'rankings.json'
API_DIR = WEB_DIR / 'api'
CARS_DIR = API_DIR / 'cars'
PAGE_SIZE = 24  # cards per page (divisible by 1,2,3,4 columns)


def load_rankings():
    """Load and sort rankings by score descending."""
    if not RANKINGS_FILE.exists():
        print(f"Error: {RANKINGS_FILE} not found!")
        return {}

    with open(RANKINGS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def resolve_car_json(json_relative_path):
    """Resolve a car's scraped JSON, handling stale date-folder paths."""
    if not json_relative_path:
        return None

    full_path = BASE_DIR / json_relative_path

    if not full_path.exists():
        try:
            finn_id = Path(json_relative_path).stem
            if finn_id.isdigit():
                candidates = list(JSON_DATA_DIR.glob(f"cars_*/{finn_id}/{finn_id}.json"))
                if candidates:
                    full_path = candidates[-1]
        except Exception:
            pass

    if not full_path.exists():
        return None

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def extract_image_url(details):
    """Extract the first usable image URL from a car's JSON-LD data."""
    image = details.get('image')
    if not image:
        return None

    if isinstance(image, list):
        image = image[0] if image else None
    if isinstance(image, dict):
        image = image.get('url') or image.get('contentUrl')
    if isinstance(image, str) and image.startswith('http'):
        return image

    return None


def hydrate_car(finn_id, ranking_entry):
    """
    Combine ranking data with scraped car details into a single
    frontend-ready object.
    """
    details = resolve_car_json(ranking_entry.get('path')) or {}
    image_url = extract_image_url(details)

    # Parse brand
    brand_raw = details.get('brand', {})
    brand = brand_raw.get('name', '') if isinstance(brand_raw, dict) else str(brand_raw or '')

    model_raw = details.get('model', '')
    model = model_raw.get('name', '') if isinstance(model_raw, dict) else str(model_raw or '')
    description = str(details.get('description', ''))

    # Truncate description for the API to keep payloads reasonable
    if len(description) > 500:
        description = description[:500] + '...'

    score = ranking_entry.get('score', 0)
    try:
        score = float(score)
    except (ValueError, TypeError):
        score = 0

    price = ranking_entry.get('price')
    try:
        price = int(price) if price else 0
    except (ValueError, TypeError):
        price = 0

    return {
        'id': finn_id,
        'name': html.escape(str(ranking_entry.get('name', 'Unknown'))),
        'brand': html.escape(brand),
        'model': html.escape(model),
        'price': price,
        'score': round(score, 1),
        'reason': html.escape(str(ranking_entry.get('reason', ''))),
        'url': ranking_entry.get('url', ''),
        'image': image_url,
        'description': html.escape(description),
        'timestamp': ranking_entry.get('timestamp', ''),
    }


def build_api():
    """Main build: generate all static JSON API files."""
    print("Loading rankings...")
    rankings = load_rankings()
    if not rankings:
        print("No rankings data. Aborting.")
        return

    # Hydrate all cars
    print(f"Hydrating {len(rankings)} cars...")
    cars = []
    for finn_id, entry in rankings.items():
        car = hydrate_car(finn_id, entry)
        cars.append(car)

    # Sort by score descending
    cars.sort(key=lambda c: c['score'], reverse=True)

    # Prepare output directory (clean rebuild)
    if API_DIR.exists():
        shutil.rmtree(API_DIR)
    CARS_DIR.mkdir(parents=True, exist_ok=True)

    # Collect filter options
    brands = sorted({c['brand'] for c in cars if c['brand']})
    total_pages = max(1, -(-len(cars) // PAGE_SIZE))  # ceil division

    # Write meta.json
    meta = {
        'total_cars': len(cars),
        'page_size': PAGE_SIZE,
        'total_pages': total_pages,
        'brands': brands,
    }
    with open(API_DIR / 'meta.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False)
    print(f"  meta.json: {len(brands)} brands, {total_pages} pages")

    # Write paginated files
    for page_num in range(1, total_pages + 1):
        start = (page_num - 1) * PAGE_SIZE
        end = start + PAGE_SIZE
        page_data = cars[start:end]

        with open(CARS_DIR / f'page-{page_num}.json', 'w', encoding='utf-8') as f:
            json.dump(page_data, f, ensure_ascii=False)

    print(f"  {total_pages} page files written to {CARS_DIR}")

    # Write lightweight all.json for client-side search/filter
    # Only include fields needed for filtering (not full description)
    all_light = []
    for c in cars:
        all_light.append({
            'id': c['id'],
            'name': c['name'],
            'brand': c['brand'],
            'model': c['model'],
            'price': c['price'],
            'score': c['score'],
            'image': c['image'],
            'reason': c['reason'],
            'url': c['url'],
        })
    with open(CARS_DIR / 'all.json', 'w', encoding='utf-8') as f:
        json.dump(all_light, f, ensure_ascii=False)
    print(f"  all.json: {len(all_light)} cars ({os.path.getsize(CARS_DIR / 'all.json') / 1024:.1f} KB)")

    print(f"SUMMARY: Built static API — {len(cars)} cars across {total_pages} pages.")


if __name__ == '__main__':
    build_api()
