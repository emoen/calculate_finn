import os
import json
import requests
import time
from datetime import datetime
from src.config import BASE_DIR, JSON_DATA_DIR, RANKINGS_DATA_DIR

# Configuration
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "xiaomi/mimo-v2-flash:free"
METADATA_FILE = os.path.join(RANKINGS_DATA_DIR, "rankings.json")
MARKET_STATS_FILE = os.path.join(RANKINGS_DATA_DIR, "market_knowledge.json")
# JSON_DATA_DIR is already imported and is a Path object, convert to str if needed by os.path.join or use / operator
# The original code used os.path.join(BASE_DIR, "json_data"), now we have JSON_DATA_DIR as Path.
# Let's ensure compatibility. mixed Path and os.path.join might fail if not str.
METADATA_FILE = str(METADATA_FILE)
MARKET_STATS_FILE = str(MARKET_STATS_FILE)
JSON_DATA_DIR = str(JSON_DATA_DIR)

def get_market_stats():
    """Load market statistics."""
    if os.path.exists(MARKET_STATS_FILE):
        try:
            with open(MARKET_STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading market stats: {e}")
            return None
    return None

def get_existing_rankings():
    """Load existing rankings from the metadata file."""
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_rankings(rankings):
    """Save rankings to the metadata file."""
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(rankings, f, indent=4, ensure_ascii=False)

import re

# ... existing imports ...

# Helper to extract year (matches logic in build_market_knowledge.py)
def extract_year(text):
    if not text: return None
    match = re.search(r'\b(20[0-2][0-9]|19[5-9][0-9])\b', str(text))
    if match:
        return int(match.group(1))
    return None

def analyze_car(car_data, market_stats_text=None):
    """Send car data to the AI model for analysis."""
    # Extract relevant fields to keep the prompt concise
    offers = car_data.get('offers', {})
    price = offers.get('price', 'Unknown')
    currency = offers.get('priceCurrency', 'NOK')
    brand_info = car_data.get('brand', {})
    brand = brand_info.get('name', '') if isinstance(brand_info, dict) else str(brand_info)
    model = car_data.get('model', '')
    name = car_data.get('name', '')
    description = car_data.get('description', '')
    url = car_data.get('url', '')

    # Truncate description if too long to avoid token limits - increased to 2500
    if len(description) > 2500:
        description = description[:2500] + "..."

    market_context = ""
    if market_stats_text:
        market_context = f"\nMARKET CONTEXT (Important):\n{market_stats_text}\n"

    prompt = f"""
    You are an expert car deal analyst. Analyze this car listing and rate how good of a deal it is on a scale of 0 to 10.
    10 is an amazing, underpriced deal. 5 is an average market price. 0 is a terrible, overpriced deal.
    
    Look closely at the description for details about:
    - Condition (low km, visible damage, recent repairs like EU-godkjent)
    - Extra equipment (winter tires included, leather seats, premium sound, etc.)
    - Seller type (dealership vs private)
    - Valid warranty (Nybilgaranti)
    {market_context}
    Car: {brand} {model}
    Title: {name}
    Price: {price} {currency}
    Description: {description}
    URL: {url}

    Return ONLY a JSON object with the following fields:
    - "score": (number, 0-10)
    - "reason": (string, a short explanation of the score, max 2 sentences)
    """

    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/endrem/calculate_finn", # Required by OpenRouter for free tier identification
        "X-Title": "Finn Car Ranker"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "response_format": { "type": "json_object" } 
    }

    retries = 3
    result = None
    for attempt in range(retries):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            
            if response.status_code != 200:
                print(f"API Error: {response.status_code} - {response.text}")
                # Don't retry on 4xx except 429
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    return None
                time.sleep(2)
                continue
                
            result = response.json()
            break
        except Exception as e:
            if attempt == retries - 1:
                print(f"Error calling AI: {e}")
                return None
            time.sleep(2 * (attempt + 1))
            
    if not result:
        return None
        
    if 'choices' in result and len(result['choices']) > 0:
        content = result['choices'][0]['message']['content']
        # Clean up potential markdown formatting
        clean_content = content.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(clean_content)
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            return None
    else:
        print("No choices in response")
        return None

def main():
    if not OPENROUTER_KEY:
        print("Error: OPENROUTER_API_KEY environment variable is not set.")
        return

    rankings = get_existing_rankings()
    print(f"Loaded {len(rankings)} existing rankings.")
    
    # Load Market Knowledge
    market_stats = get_market_stats()
    if market_stats:
        print(f"Loaded market knowledge for {len(market_stats.get('models', {}))} models and {len(market_stats.get('brands', {}))} brands.")
    else:
        print("Warning: No market knowledge found. AI will fly blind.")

    print(f"Scanning directory: {JSON_DATA_DIR}")
    
    count = 0
    # Walk through the json_data directory
    for root, dirs, files in os.walk(JSON_DATA_DIR):
        # Skip 'pages' directories and 'solgt' directories if any
        if 'pages' in root.split(os.sep) or 'solgt' in root.split(os.sep):
            continue

        for file in files:
            if file.endswith(".json") and file != "analysis.json":
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    finn_id = data.get('finn_id')
                    
                    # Fallback if finn_id missing in file content (use filename)
                    if not finn_id:
                        finn_id = os.path.splitext(file)[0]
                        data['finn_id'] = finn_id # Ensure it's in data for consistency

                    # Skip if already ranked
                    if finn_id in rankings:
                        continue

                    # Check for existing analysis.json
                    analysis_file_path = os.path.join(os.path.dirname(file_path), "analysis.json")
                    if os.path.exists(analysis_file_path):
                        try:
                            with open(analysis_file_path, 'r', encoding='utf-8') as af:
                                analysis = json.load(af)
                                print(f"Found existing analysis for {finn_id}, loading local.")
                        except Exception as e:
                            print(f"Error loading existing analysis: {e}")
                            analysis = None
                    else:
                        print(f"Ranking car {finn_id} ({data.get('name', 'Unknown')})...")
                        
                        # Prepare Market Stats Context
                        market_stats_text = None
                        if market_stats:
                            brand_info = data.get('brand', {})
                            brand_name = brand_info.get('name', '') if isinstance(brand_info, dict) else str(brand_info)
                            brand_clean = str(brand_name).strip().lower()
                            if brand_clean == 'vw': brand_clean = 'volkswagen'
                            
                            model_name = str(data.get('model', '')).strip().lower()
                            model_key = f"{brand_clean} {model_name}"
                            
                            stats = market_stats.get('models', {}).get(model_key)
                            
                            if stats:
                                # Start with base model stats
                                lines = [
                                    f"Market Stats for {brand_clean} {model_name} ({stats['count']} listings):",
                                    f"- Overall Avg Price: {stats['avg']} NOK",
                                    f"- Overall Median: {stats['median']} NOK",
                                    f"- Overall Range: {stats['min']} - {stats['max']} NOK"
                                ]
                                
                                # 1. Extract and Add Year specific stats
                                car_year = extract_year(data.get('name', '')) or extract_year(data.get('description', ''))
                                if car_year:
                                    year_stats = stats.get('years', {}).get(str(car_year))
                                    if year_stats:
                                        lines.append(f"- {car_year} Models (Specific): Avg {year_stats['avg']} NOK | Median {year_stats['median']} NOK")
                                
                                # 2. Extract and Add Seller Type stats
                                offers = data.get('offers', {})
                                seller_type = offers.get('seller', {}).get('@type', 'Person')
                                seller_key = 'dealer' if seller_type == 'Organization' else 'private'
                                seller_stats = stats.get('sellers', {}).get(seller_key)
                                if seller_stats:
                                    lines.append(f"- {seller_key.capitalize()} Sellers (Specific): Avg {seller_stats['avg']} NOK | Median {seller_stats['median']} NOK")
                                
                                market_stats_text = "\n".join(lines)
                            
                            # Fallback to Brand stats if model not found
                            elif market_stats.get('brands', {}).get(brand_clean):
                                stats = market_stats.get('brands', {}).get(brand_clean)
                                market_stats_text = (
                                    f"Broad Brand Stats for {brand_clean} ({stats['count']} listings):\n"
                                    f"- Avg Price: {stats['avg']} NOK"
                                )

                        analysis = analyze_car(data, market_stats_text)

                    if analysis:
                        # Save analysis to local folder
                        try:
                            analysis_path = os.path.join(os.path.dirname(file_path), "analysis.json")
                            with open(analysis_path, 'w', encoding='utf-8') as af:
                                json.dump(analysis, af, indent=4, ensure_ascii=False)
                        except Exception as e:
                            print(f"Failed to save local analysis file: {e}")

                        rankings[finn_id] = {
                            "score": analysis.get("score"),
                            "reason": analysis.get("reason"),
                            "timestamp": datetime.now().isoformat(),
                            "path": os.path.relpath(file_path, BASE_DIR),
                            "name": data.get('name', ''),
                            "price": data.get('offers', {}).get('price'),
                            "url": data.get('url', '')
                        }
                        
                        count += 1
                        # Save every update to prevent data loss
                        save_rankings(rankings)
                        print(f"  -> Score: {analysis.get('score')} - {analysis.get('reason')}")
                        
                        # Sleep briefly to be nice to the free API
                        time.sleep(2)
                    else:
                        print("  -> Failed to analyze.")
                        
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")

    print(f"Finished. Ranked {count} new cars.")

if __name__ == "__main__":
    main()
