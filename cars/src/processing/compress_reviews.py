import os
import json
import time
import requests
from pathlib import Path
from src.config import DATA_REVIEWS_DIR, BASE_DIR
from src.model_rotation import call_llm, get_current_model

API_URL = "https://openrouter.ai/api/v1/chat/completions"

COMPRESSED_DIR = BASE_DIR / "data_reviews_compressed"

def ensure_dir():
    if not COMPRESSED_DIR.exists():
        COMPRESSED_DIR.mkdir(parents=True)

def compress_branding_info(brand, model, reviews):
    """
    Compresses a list of reviews into a single structured JSON summary.
    """
    
    # helper to truncate if too large (naive)
    # Gemini 2.0 Flash has a large window, but let's be safe-ish
    # Concatenate all text
    combined_text = ""
    for r in reviews:
        combined_text += f"\n--- Review from {r.get('source', 'Unknown')} ---\n"
        combined_text += f"Title: {r.get('title', '')}\n"
        combined_text += f"Summary: {r.get('summary', '')}\n"
        combined_text += f"Body: {r.get('text', '')}\n"

    prompt = f"""
    You are an expert automotive analyst. Analyze the following reviews for the {brand} {model}.
    Extract and summarize the "important information" into a clean JSON structure.
    
    Target JSON Structure:
    {{
        "brand": "{brand}",
        "model": "{model}",
        "score": 0, // Integer 0-100 based on the overall sentiment/verdict of the reviews
        "pros": ["string", "string"],
        "cons": ["string", "string"],
        "scraped_price_info": "string (mention specific prices if found)",
        "driving_dynamics": "string summary",
        "comfort_and_practicality": "string summary",
        "reliability_issues": ["string", "string"],
        "verdict_summary": "string"
    }}

    Reviews content:
    {combined_text}
    """

    print(f"  Sending request to {get_current_model('compress')} for {brand} {model}...")

    messages = [{"role": "user", "content": prompt}]
    result = call_llm(
        task="compress",
        messages=messages,
        response_format={"type": "json_object"},
        timeout=60,
        referer="http://localhost:3000",
        title="CarRankingApp",
    )

    if result and 'choices' in result and len(result['choices']) > 0:
        try:
            content = result['choices'][0]['message']['content']
            return json.loads(content)
        except Exception as e:
            print(f"  Error parsing response: {e}")

    return None

def main():
    ensure_dir()
    
    if not DATA_REVIEWS_DIR.exists():
        print(f"No reviews directory found at {DATA_REVIEWS_DIR}")
        return

    # Iterate over all JSON files in data_reviews
    for item in os.listdir(DATA_REVIEWS_DIR):
        if item.endswith(".json"):
            file_path = DATA_REVIEWS_DIR / item
            
            # Check if output already exists (skip optimization)
            output_path = COMPRESSED_DIR / item
            if output_path.exists():
                print(f"Skipping {item} (already compressed)")
                continue
                
            print(f"Processing {item}...")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            brand = data.get('brand', 'Unknown')
            model = data.get('model', 'Unknown')
            reviews = data.get('reviews', [])
            
            if not reviews:
                print("  No reviews to process.")
                continue
                
            compressed_data = compress_branding_info(brand, model, reviews)
            
            if compressed_data:
                # Add metadata
                compressed_data['source_file'] = item
                compressed_data['processed_date'] = time.strftime("%Y-%m-%d")
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(compressed_data, f, indent=4, ensure_ascii=False)
                print(f"  Saved compressed data to {output_path}")
            
            # Sleep briefly to avoid rate limits if any
            time.sleep(1)

if __name__ == "__main__":
    main()
