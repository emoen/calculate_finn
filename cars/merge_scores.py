import json
import os
import pandas as pd
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).resolve().parent
JSON_DATA_DIR = BASE_DIR / 'json_data' / 'cars_20012026'
ML_SCORES_FILE = BASE_DIR / 'ml_scores.json'
OUTPUT_FILE = BASE_DIR / 'comparison_scores.json'

def load_ml_scores():
    if not ML_SCORES_FILE.exists():
        return {}
    with open(ML_SCORES_FILE, 'r') as f:
        return json.load(f)

def get_llm_scores():
    llm_scores = {}
    print(f"Scanning {JSON_DATA_DIR} for analysis.json...")
    for root, dirs, files in os.walk(JSON_DATA_DIR):
        if "analysis.json" in files:
            path = os.path.join(root, "analysis.json")
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    # Assuming folder name is finn_id, or we need to extract from path
                    # cars/json_data/cars_20012026/138211802/analysis.json -> id is 138211802
                    finn_id = os.path.basename(root)
                    
                    score = data.get('score')
                    if score is not None:
                        llm_scores[finn_id] = float(score)
            except Exception:
                continue
    return llm_scores

def main():
    ml_scores = load_ml_scores()
    llm_scores = get_llm_scores()
    
    print(f"Loaded {len(ml_scores)} ML scores.")
    print(f"Loaded {len(llm_scores)} LLM scores.")
    
    combined = {}
    all_ids = set(ml_scores.keys()) | set(llm_scores.keys())
    
    points = []
    
    for finn_id in all_ids:
        m = ml_scores.get(finn_id)
        l = llm_scores.get(finn_id)
        
        entry = {}
        if m is not None: entry['ml_score'] = m
        if l is not None: entry['llm_score'] = l
        
        combined[finn_id] = entry
        
        if m is not None and l is not None:
            points.append({'ml': m, 'llm': l})
            
    # Save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(combined, f, indent=4)
    print(f"Saved comparison to {OUTPUT_FILE}")
    
    # Analysis
    if len(points) > 1:
        df = pd.DataFrame(points)
        correlation = df['ml'].corr(df['llm'])
        print(f"Correlation between ML and LLM scores: {correlation:.4f}")
        print("Stats:")
        print(df.describe())
    else:
        print("Not enough overlapping scores for correlation analysis.")

if __name__ == "__main__":
    main()
