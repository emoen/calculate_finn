import requests
import json
import sys
import os

# Add parent directory to path to enable importing 'src' modules when running directly
current_dir = os.path.dirname(os.path.abspath(__file__)) # .../cars/src
parent_dir = os.path.dirname(current_dir) # .../cars
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from src.analysis.rank_cars import OPENROUTER_KEY as RANK_KEY, MODEL as RANK_MODEL
    from src.processing.compress_reviews import MODEL_KEY as COMPRESS_KEY, MODEL_NAME as COMPRESS_MODEL
except ImportError:
    # Fallback/Debug if structure is slightly different or run from different CWD
    try:
        from analysis.rank_cars import OPENROUTER_KEY as RANK_KEY, MODEL as RANK_MODEL
        from processing.compress_reviews import MODEL_KEY as COMPRESS_KEY, MODEL_NAME as COMPRESS_MODEL
    except ImportError as e:
        print(f"Error importing model configs: {e}")
        sys.exit(1)

API_URL = "https://openrouter.ai/api/v1/chat/completions"

def check_model(name, key, model):
    if not key:
        return f"{name}: FAIL (No Key)"
    
    headers = {
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "https://github.com/endrem/calculate_finn",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 1
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
             return f"{name}: OK"
        else:
             return f"{name}: FAIL ({response.status_code})"
    except Exception as e:
        return f"{name}: FAIL ({str(e)})"

def main():
    print("Checking model connectivity...")
    
    res2 = check_model("Compress Reviews", COMPRESS_KEY, COMPRESS_MODEL)
    res1 = check_model("Rank Cars", RANK_KEY, RANK_MODEL)
    print(f"SUMMARY: Model Check - {res1}, {res2}")

if __name__ == "__main__":
    main()
