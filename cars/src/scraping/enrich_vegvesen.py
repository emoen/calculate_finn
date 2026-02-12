import os
import json
import requests
import time
from bs4 import BeautifulSoup
from src.config import JSON_DATA_DIR

def get_car_ids():
    ids = []
    if JSON_DATA_DIR.exists():
        for date_dir in os.listdir(JSON_DATA_DIR):
            dir_path = JSON_DATA_DIR / date_dir
            if dir_path.is_dir() and date_dir.startswith('cars_'):
                for item in os.listdir(dir_path):
                    if item.isdigit():
                        ids.append((item, dir_path / item))
    return ids

def fetch_details_from_finn(finn_id):
    url = f"https://www.finn.no/mobility/item/{finn_id}"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def parse_technical_data(html):
    soup = BeautifulSoup(html, 'html.parser')
    data = {}
    
    # Finn uses Definition Lists (dl) often for specs
    # Format usually: <dt>Label</dt><dd>Value</dd>
    
    # Try different selectors common on Finn
    dls = soup.find_all('dl')
    for dl in dls:
        dts = dl.find_all('dt')
        dds = dl.find_all('dd')
        if len(dts) == len(dds):
            for dt, dd in zip(dts, dds):
                key = dt.get_text(strip=True).replace(':', '')
                val = dd.get_text(strip=True)
                data[key] = val
                
    # Specific extraction for Regnr if not found in DL
    # Sometimes it is just in the detailed specs section
    
    # Normalize keys
    normalized = {}
    mapping = {
        "Reg.nr.": "registration_number",
        "Registreringsnummer": "registration_number",
        "Chassis nr. (VIN)": "vin",
        "EU-godkjent til": "eu_control_expires",
        "Sist EU-godkjent": "last_eu_control",
        "Effekt": "horsepower",
        "Vekt": "weight",
        "CO2-utslipp": "co2_emissions"
    }
    
    for k, v in data.items():
        if k in mapping:
            normalized[mapping[k]] = v
        # Also keep original if useful
        # normalized[k] = v 
        
    return normalized

def main():
    print("Starting enrichment with technical data (Vegvesen/Finn specs)...")
    car_ids = get_car_ids()
    print(f"Found {len(car_ids)} cars to check.")
    
    count = 0
    for finn_id, folder_path in car_ids:
        output_file = folder_path / "vegvesen.json"
        
        if output_file.exists():
            continue
            
        print(f"Enriching {finn_id}...")
        html = fetch_details_from_finn(finn_id)
        if html:
            info = parse_technical_data(html)
            
            # Additional fallback: if empty, maybe the car is sold/gone, verify in HTML
            if not info:
                print(f"  No technical specs found for {finn_id} (Sold/Expired?)")
            
            # Save whatever we found, even if empty, to mark as processed/attempted?
            # Better to save only if we have data or explicit failure note
            if info:
                info['fetched_at'] = time.strftime("%Y-%m-%d %H:%M:%S")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(info, f, indent=4, ensure_ascii=False)
                count += 1
                
        # Be nice to the server
        time.sleep(1)
        
    print(f"Finished. Enriched {count} new cars.")

if __name__ == "__main__":
    main()
