import json
import os
from pathlib import Path
# from tabulate import tabulate 

# Determine paths (relative to where script is run, assuming from cars/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
COMPRESSED_DIR = BASE_DIR / "data_reviews_compressed"

def main():
    if not COMPRESSED_DIR.exists():
        print(f"Directory not found: {COMPRESSED_DIR}")
        return

    scores = []
    
    files = list(COMPRESSED_DIR.glob("*.json"))
    if not files:
        print("No compressed review files found.")
        return

    print(f"Reading {len(files)} files...\n")

    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            brand = data.get('brand', 'Unknown')
            model = data.get('model', 'Unknown')
            score = data.get('score', 0)
            
            # Ensure score is an integer
            try:
                score = int(score)
            except (ValueError, TypeError):
                score = 0
                
            scores.append({
                "car": f"{brand} {model}",
                "score": score
            })
        except Exception as e:
            print(f"Error reading {file_path.name}: {e}")

    # Sort descending
    scores.sort(key=lambda x: x['score'], reverse=True)

    # Print
    print(f"{'Rank':<5} | {'Score':<5} | {'Car':<30}")
    print("-" * 50)
    for idx, item in enumerate(scores, 1):
        print(f"{idx:<5} | {item['score']:<5} | {item['car']:<30}")

if __name__ == "__main__":
    main()
