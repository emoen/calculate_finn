import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
from src.config import BASE_DIR, JSON_DATA_DIR, RANKINGS_DATA_DIR
from src.utils import extract_year, extract_mileage, normalize_brand

# Configuration
# Keep hardcoded subfolder for now as it was specific
JSON_DATA_DIR_SPECIFIC = JSON_DATA_DIR / 'cars_20012026'
MARKET_KNOWLEDGE_FILE = RANKINGS_DATA_DIR / 'market_knowledge.json'
SCORES_OUTPUT_FILE = RANKINGS_DATA_DIR / 'ml_scores.json'

def load_market_knowledge():
    if not MARKET_KNOWLEDGE_FILE.exists():
        print("Market knowledge file not found.")
        return {}
    with open(MARKET_KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def normalize_string(s):
    if not s:
        return ""
    return str(s).strip().lower()

def extract_features_from_text(text):
    text = normalize_string(text)
    features = {}
    
    # Year and Mileage from shared utils
    features['year'] = extract_year(text)
    features['mileage'] = extract_mileage(text)

    # Horsepower
    import re
    hk_match = re.search(r'(\d+)\s*(?:hk|hester)', text)
    if hk_match:
        try:
            features['power'] = int(hk_match.group(1))
        except (ValueError, TypeError):
            pass
            
    # Fuel
    if 'diesel' in text:
        features['fuel'] = 'diesel'
    elif 'bensin' in text:
        features['fuel'] = 'gasoline'
    elif 'elektrisk' in text or 'elbil' in text:
        features['fuel'] = 'electric'
    elif 'hybrid' in text:
        features['fuel'] = 'hybrid'
        
    # Transmission
    if 'automat' in text:
        features['transmission'] = 'automatic'
    elif 'manuell' in text:
        features['transmission'] = 'manual'
        
    return features

def get_car_data(market_data):
    cars = []
    
    if not JSON_DATA_DIR.exists():
        print(f"Data directory {JSON_DATA_DIR} not found.")
        return pd.DataFrame()

    print(f"Scanning {JSON_DATA_DIR}...")
    
    for root, dirs, files in os.walk(JSON_DATA_DIR):
        for file in files:
            if file.endswith(".json") and file != "analysis.json":
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception:
                    continue
                
                # Check if data is list (some schema.org dumps are lists of objects)
                if isinstance(data, list):
                    # Try to find the Product or valid item in the list
                    found_data = None
                    for item in data:
                        if isinstance(item, dict) and item.get('finn_id'):
                            found_data = item
                            break
                    if found_data:
                        data = found_data
                    else:
                        continue
                
                if not isinstance(data, dict):
                    continue

                # Basic fields
                finn_id = data.get('finn_id')
                if not finn_id:
                    continue
                
                price = None
                offers = data.get('offers', {})
                if isinstance(offers, dict):
                    price = offers.get('price')
                
                if not price:
                    continue
                
                try:
                    price = int(price)
                except ValueError:
                    continue

                brand = data.get('brand', {}).get('name') if isinstance(data.get('brand'), dict) else data.get('brand')
                model = data.get('model')
                
                text_content = f"{data.get('name', '')} {data.get('description', '')}"
                extracted = extract_features_from_text(text_content)
                
                car_entry = {
                    'finn_id': finn_id,
                    'price': price,
                    'brand': normalize_string(brand),
                    'model': normalize_string(model),
                    'year': extracted.get('year'),
                    'mileage': extracted.get('mileage'),
                    'power': extracted.get('power'),
                    'fuel': extracted.get('fuel', 'unknown'),
                    'transmission': extracted.get('transmission', 'unknown')
                }
                
                # Add Market Context
                brand_key = normalize_brand(car_entry['brand'])
                model_key = f"{brand_key} {car_entry['model']}"
                
                market_avg = None
                market_min = None
                market_max = None
                
                # Try specific year stats first
                if car_entry['year']:
                     year_str = str(car_entry['year'])
                     model_stats = market_data.get('models', {}).get(model_key, {})
                     year_stats = model_stats.get('years', {}).get(year_str)
                     
                     if year_stats:
                         market_avg = year_stats.get('avg')
                         market_min = year_stats.get('min')
                         market_max = year_stats.get('max')
                
                # Fallback to model stats
                if market_avg is None:
                    model_stats = market_data.get('models', {}).get(model_key, {})
                    market_avg = model_stats.get('avg')
                    market_min = model_stats.get('min')
                    market_max = model_stats.get('max')

                car_entry['market_avg'] = market_avg
                car_entry['market_min'] = market_min
                car_entry['market_max'] = market_max
                
                cars.append(car_entry)
                
    return pd.DataFrame(cars)

def train_and_score():
    print("Loading market knowledge...")
    market_data = load_market_knowledge()
    
    print("Loading and extracting car data...")
    df = get_car_data(market_data)
    
    if df.empty:
        print("No car data found.")
        return

    print(f"Loaded {len(df)} cars.")
    
    # Preprocessing
    # Drop rows without critical info for training? 
    # Actually, for the target score, we want to score ALL cars, even if we drop them from training.
    # So we split: Train Set (clean data) vs Score Set (all data)
    
    # We need to impute missing values for the model
    # Impute year with median, mileage with median
    df['year'] = df['year'].fillna(df['year'].median())
    df['mileage'] = df['mileage'].fillna(df['mileage'].median())
    df['power'] = df['power'].fillna(df['power'].median())
    df['market_avg'] = df['market_avg'].fillna(df['price']) # Fallback to own price minimizes error for unknown models
    
    # Define feature columns
    numeric_features = ['year', 'mileage', 'power', 'market_avg']
    categorical_features = ['brand', 'fuel', 'transmission']
    
    # Build a Pipeline with OneHotEncoder for categorical features
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', 'passthrough', numeric_features),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features),
        ]
    )
    
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=100, random_state=42)),
    ])

    features = numeric_features + categorical_features
    target = 'price'
    
    # Train
    X = df[features]
    y = df[target]
    
    # Split for validation
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training Random Forest Regressor with OneHotEncoder...")
    pipeline.fit(X_train, y_train)
    
    y_pred = pipeline.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print(f"Model Performance: MAE={mae:.2f}, R2={r2:.2f}")
    
    # Predict for ALL cars
    full_predictions = pipeline.predict(X)
    df['predicted_price'] = full_predictions
    
    # Calculate Score
    # Score logic: A higher score means it's a better deal (Actual Price is lower than Predicted Price)
    # Ratio = Predicted / Actual
    # If Ratio = 1.0 (Fair price), Score ~ 5
    # If Ratio = 1.2 (20% underpriced), Score ~ 7-8
    # If Ratio = 0.8 (20% overpriced), Score ~ 2-3
    
    def calculate_score(predicted, actual):
        if actual == 0: return 0
        ratio = predicted / actual
        # Sigmoid-like mapping or linear?
        # Let's use simple linear for now, capped.
        # Ratio 1.0 -> 5.0
        # Ratio 1.5 -> 10.0
        # Ratio 0.5 -> 0.0
        score = 5.0 * ratio
        return min(max(score, 0.0), 10.0)

    df['ml_score'] = df.apply(lambda row: calculate_score(row['predicted_price'], row['price']), axis=1)
    
    # Export scores
    scores_dict = {}
    for _, row in df.iterrows():
        scores_dict[str(row['finn_id'])] = round(row['ml_score'], 2)
        
    print(f"Saving scores to {SCORES_OUTPUT_FILE}...")
    SCORES_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCORES_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(scores_dict, f, indent=4)
        
    print(f"SUMMARY: Model trained. MAE: {mae:.2f}, R2: {r2:.2f}. Scores generated for {len(scores_dict)} cars.")

if __name__ == "__main__":
    train_and_score()
