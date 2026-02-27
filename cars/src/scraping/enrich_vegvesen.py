import os
import json
import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup
from src.config import JSON_DATA_DIR

def get_car_id_locations():
    locations = {}
    if JSON_DATA_DIR.exists():
        for date_dir in os.listdir(JSON_DATA_DIR):
            dir_path = JSON_DATA_DIR / date_dir
            if dir_path.is_dir() and date_dir.startswith('cars_'):
                for item in os.listdir(dir_path):
                    if item.isdigit():
                        locations.setdefault(item, []).append(dir_path / item)
    return locations

def get_folder_id_counts():
    folder_counts = {}
    if JSON_DATA_DIR.exists():
        for date_dir in sorted(os.listdir(JSON_DATA_DIR)):
            dir_path = JSON_DATA_DIR / date_dir
            if dir_path.is_dir() and date_dir.startswith('cars_'):
                id_count = 0
                for item in os.listdir(dir_path):
                    if item.isdigit():
                        id_count += 1
                folder_counts[date_dir] = id_count
    return folder_counts

def get_folder_pending_counts(id_locations, completed_ids):
    pending_counts = {}
    for finn_id, folder_paths in id_locations.items():
        if finn_id in completed_ids:
            continue

        newest_folder = sorted(folder_paths, key=date_sort_key)[-1]
        folder_name = newest_folder.parent.name
        pending_counts[folder_name] = pending_counts.get(folder_name, 0) + 1
    return pending_counts

def get_completed_finn_ids():
    completed_ids = set()
    if JSON_DATA_DIR.exists():
        for date_dir in os.listdir(JSON_DATA_DIR):
            dir_path = JSON_DATA_DIR / date_dir
            if dir_path.is_dir() and date_dir.startswith('cars_'):
                for item in os.listdir(dir_path):
                    if item.isdigit() and (dir_path / item / "vegvesen.json").exists():
                        completed_ids.add(item)
    return completed_ids

def date_sort_key(folder_path):
    folder_name = folder_path.parent.name
    if folder_name.startswith("cars_"):
        try:
            return datetime.strptime(folder_name.replace("cars_", ""), "%d%m%Y")
        except ValueError:
            pass
    return datetime.min

def write_vegvesen_json(output_file, info):
    json_content = json.dumps(info, indent=4, ensure_ascii=False)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(json_content)
    return len(json_content.splitlines())

def fetch_details_from_finn(finn_id):
    url = f"https://www.finn.no/mobility/item/{finn_id}"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            return response.text, None
        return None, f"HTTP {response.status_code}"
    except requests.RequestException as e:
        return None, str(e)

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
    id_locations = get_car_id_locations()
    completed_ids = get_completed_finn_ids()
    folder_id_counts = get_folder_id_counts()
    folder_pending_counts = get_folder_pending_counts(id_locations, completed_ids)

    all_unique_ids = sorted(id_locations.keys(), key=int)
    pending_ids = [finn_id for finn_id in all_unique_ids if finn_id not in completed_ids]

    total_ids = len(all_unique_ids)
    total_pending = len(pending_ids)

    print(f"Found {total_ids} unique FINN IDs.")
    print(f"Already enriched IDs: {len(completed_ids)}")
    print(f"Pending IDs to enrich: {total_pending}")
    if folder_id_counts:
        folder_count_text = ", ".join(
            f"{folder}: {count}" for folder, count in folder_id_counts.items()
        )
        print(f"Included folders (ID counts): {folder_count_text}")

    if folder_pending_counts:
        top_pending = sorted(
            folder_pending_counts.items(), key=lambda item: item[1], reverse=True
        )[:5]
        print("Top 5 folders by pending IDs:")
        for rank, (folder, count) in enumerate(top_pending, start=1):
            print(f"  {rank}. {folder}: {count}")

    if total_pending == 0:
        print("Nothing to do. All FINN IDs already have vegvesen enrichment.")
        return
    
    count_ids_enriched = 0
    count_files_written = 0

    for index, finn_id in enumerate(pending_ids, start=1):
        print(f"Enriching vegvesen finn_id {finn_id}...", end="")
        html, fetch_error = fetch_details_from_finn(finn_id)
        if html:
            info = parse_technical_data(html)

            if info:
                info['fetched_at'] = time.strftime("%Y-%m-%d %H:%M:%S")
                target_folders = sorted(id_locations.get(finn_id, []), key=date_sort_key)
                wrote_for_this_id = False
                line_counts = []
                for folder_path in target_folders:
                    output_file = folder_path / "vegvesen.json"
                    if output_file.exists():
                        continue

                    line_count = write_vegvesen_json(output_file, info)
                    count_files_written += 1
                    wrote_for_this_id = True
                    line_counts.append(line_count)

                if wrote_for_this_id:
                    count_ids_enriched += 1
                    if len(line_counts) == 1:
                        print(f" ({line_counts[0]} lines)")
                    else:
                        print(f" ({line_counts[0]} lines x {len(line_counts)} files)")
                else:
                    print(" (already enriched)")
            else:
                print(" (no technical specs found)")
        else:
            print(f" (fetch failed: {fetch_error})")

        if index % 10 == 0 or index == total_pending:
            progress_pct = (index / total_pending) * 100
            print(
                f"Progress: {index}/{total_pending} FINN IDs ({progress_pct:.1f}%) | "
                f"enriched IDs: {count_ids_enriched} | files written: {count_files_written}"
            )
                
        # Be nice to the server
        time.sleep(1)
        
    print(
        f"Finished. Enriched {count_ids_enriched} FINN IDs and wrote {count_files_written} vegvesen files."
    )

if __name__ == "__main__":
    main()
