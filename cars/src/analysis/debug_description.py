import requests
from bs4 import BeautifulSoup
import json

url = "https://www.finn.no/mobility/item/446971528"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

print("--- JSON-LD Data ---")
script_tags = soup.find_all('script', type='application/ld+json')
found_json_desc = False
for script in script_tags:
    if script.string:
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                for item in data:
                    if item.get('@type') in ['Product', 'Vehicle', 'Car', 'MotorCycle']:
                        print(f"JSON-LD Description found: {item.get('description', 'N/A')[:100]}...")
                        found_json_desc = True
            elif isinstance(data, dict):
                 if data.get('@type') in ['Product', 'Vehicle', 'Car', 'MotorCycle']:
                    print(f"JSON-LD Description found: {data.get('description', 'N/A')[:100]}...")
                    found_json_desc = True
        except:
            pass

if not found_json_desc:
    print("No description found in JSON-LD schemas of interest.")

print("\n--- HTML Body Search ---")
# Look for the specific text provided by user to find the container
target_text = "Mustang Mach-E er den perfekte kombinasjonen"
element = soup.find(string=lambda text: text and target_text in text)
if element:
    parent = element.parent
    print(f"Found text in tag: <{parent.name} class='{parent.get('class', [])}'>")
    # Print the full content of the parent to see if it's the right container
    print(f"Content snippet: {parent.get_text()[:200]}...")
    
    # Check for common Finn description classes
    description_div = soup.find('div', class_='import-decoration')
    if description_div:
         print(f"Found div.import-decoration. Snippet: {description_div.get_text()[:100]}...")
    
