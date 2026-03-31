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
    from src.model_rotation import PROVIDERS
except ImportError:
    try:
        from model_rotation import PROVIDERS
    except ImportError as e:
        print(f"Error importing model configs: {e}")
        sys.exit(1)


def check_model(api_url, key, model):
    if not key:
        return f"  {model}: FAIL (No Key)"
    
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
        response = requests.post(api_url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
             return f"  {model}: OK"
        else:
             return f"  {model}: FAIL ({response.status_code})"
    except Exception as e:
        return f"  {model}: FAIL ({str(e)})"

def main():
    print("Checking model connectivity...\n")
    
    total_ok = 0
    total_count = 0
    
    for provider in PROVIDERS:
        name = provider["name"]
        url = provider["url"]
        key = provider["key"]
        # Deduplicate models across ranking + compress for this provider
        all_models = list(dict.fromkeys(
            provider["ranking_models"] + provider["compress_models"]
        ))
        
        print(f"--- {name} ({len(all_models)} models) ---")
        for model in all_models:
            result = check_model(url, key, model)
            print(result)
            total_count += 1
            if "OK" in result:
                total_ok += 1
        print()
    
    fail_count = total_count - total_ok
    print(f"SUMMARY: Model Check - {total_ok}/{total_count} OK, {fail_count} failed")

if __name__ == "__main__":
    main()
