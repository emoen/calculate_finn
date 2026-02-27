import os
import json
import statistics
import re
from collections import defaultdict
from pathlib import Path
from src.config import BASE_DIR, JSON_DATA_DIR, RANKINGS_DATA_DIR

# Configuration
OUTPUT_FILE = RANKINGS_DATA_DIR / 'market_knowledge.json'

def get_all_cars():
    """Generator to yield all car data from json_data directory."""
    for root, dirs, files in os.walk(JSON_DATA_DIR):
        if 'solgt' in root.split(os.sep):
            continue
            
        for file in files:
            if file.endswith(".json") and file != "analysis.json":
                try:
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        yield json.load(f)
                except Exception as e:
                    # Silently skip broken files
                    continue

def normalize_key(brand, model):
    """Create a consistent key for grouping."""
    b = str(brand).strip().lower()
    m = str(model).strip().lower()
    
    # Common normalizations
    if b == 'vw': b = 'volkswagen'
    
    return f"{b} {m}"

def extract_year(text):
    """Extract 4-digit year starting with 20 or 19 from text."""
    if not text: return None
    match = re.search(r'\b(20[0-2][0-9]|19[5-9][0-9])\b', str(text))
    if match:
        return int(match.group(1))
    return None

def extract_mileage(text):
    """Extract mileage in km from text."""
    if not text: return None
    # Matches patterns like "50 000 km", "50.000km", "50000 km"
    match = re.search(r'(\d+[\s\.]?\d*)\s*(?:km|kilometer)', str(text).lower())
    if match:
        try:
            # Clean string like "50 000" -> "50000"
            clean_num = match.group(1).replace(' ', '').replace('.', '')
            val = int(clean_num)
            # Sanity check: Car with > 1M km is unlikely or error
            if 0 < val < 1000000:
                return val
        except:
            pass
    return None

def calculate_stats(prices):
    if not prices:
        return None
    
    sorted_prices = sorted(prices)
    n = len(prices)
    
    return {
        "count": n,
        "min": sorted_prices[0],
        "max": sorted_prices[-1],
        "avg": int(statistics.mean(prices)),
        "median": int(statistics.median(prices)),
        "p25": int(sorted_prices[int(n * 0.25)]) if n > 3 else sorted_prices[0],
        "p75": int(sorted_prices[int(n * 0.75)]) if n > 3 else sorted_prices[-1]
    }

def main():
    print("Building extended market knowledge base...")
    
    # Storage
    model_prices = defaultdict(list)
    model_year_prices = defaultdict(list)   # key: "brand model|year"
    model_seller_prices = defaultdict(list) # key: "brand model|seller_type"
    brand_prices = defaultdict(list)
    
    count = 0
    for car in get_all_cars():
        # improved brand parsing
        brand_raw = car.get('brand')
        if isinstance(brand_raw, dict):
            brand = brand_raw.get('name', 'unknown')
        else:
            brand = brand_raw or 'unknown'
            
        model = car.get('model', 'unknown')
        name = car.get('name', '')
        description = car.get('description', '')
        
        # Price parsing
        offers = car.get('offers', {})
        if isinstance(offers, dict):
            price = offers.get('price')
            seller_type = offers.get('seller', {}).get('@type', 'Person') # Default to Person if unknown
        else:
            price = None
            seller_type = 'Person'
            
        # Refine seller type to just 'Dealer' or 'Private'
        if seller_type == 'Organization':
            seller_clean = 'dealer'
        else:
            seller_clean = 'private'

        # Skip if key data is missing
        if not price or str(price).lower() == 'unknown':
            continue
            
        try:
            price = int(price)
        except ValueError:
            continue
            
        # Normalize Key
        key = normalize_key(brand, model)
        brand_key = str(brand).strip().lower()
        if brand_key == 'vw': brand_key = 'volkswagen'

        # Extract Extra Stats
        year = extract_year(name)
        if not year:
            year = extract_year(description)
            
        # Store Data
        model_prices[key].append(price)
        brand_prices[brand_key].append(price)
        model_seller_prices[f"{key}|{seller_clean}"].append(price)
        
        if year:
            model_year_prices[f"{key}|{year}"].append(price)
            
        count += 1
        
    print(f"Processed {count} valid listings.")
    
    # Calculate Statistics
    market_stats = {
        "metadata": {
            "total_listings": count,
            "generated_at": str(os.path.getmtime(__file__)) 
        },
        "models": {},
        "brands": {}
    }
    
    print("Calculating statistics...")
    
    # 1. Base Model Stats + Segments
    for key, prices in model_prices.items():
        if len(prices) >= 3:
            stats = calculate_stats(prices)
            
            # Embed advanced stats inside the model object
            stats["years"] = {}
            stats["sellers"] = {}
            
            # Fill Years
            # key looks like "volvo xc90". check model_year_prices keys starting with this.
            # actually we constructed strings like "volvo xc90|2021"
            # Optimization: could iterate existing keys or just range reasonable years
            current_years = [y for y in range(2000, 2027) if f"{key}|{y}" in model_year_prices]
            for y in current_years:
                y_prices = model_year_prices[f"{key}|{y}"]
                if len(y_prices) >= 2: # Lower threshold for substats
                     stats["years"][str(y)] = calculate_stats(y_prices)
                     
            # Fill Sellers
            for s_type in ['dealer', 'private']:
                s_prices = model_seller_prices[f"{key}|{s_type}"]
                if len(s_prices) >= 2:
                    stats["sellers"][s_type] = calculate_stats(s_prices)

            market_stats["models"][key] = stats
            
    # 2. Brand Stats
    for key, prices in brand_prices.items():
        if len(prices) >= 5:
            stats = calculate_stats(prices)
            market_stats["brands"][key] = stats
            
    print(f"Generated extended stats for {len(market_stats['models'])} models and {len(market_stats['brands'])} brands.")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(market_stats, f, indent=4)
        
    print(f"Market knowledge saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
