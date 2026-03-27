import os
import json
import requests
import time
import re
from slugify import slugify # Might need to install this or implement simple slugify
from bs4 import BeautifulSoup
from src.config import JSON_DATA_DIR, DATA_REVIEWS_DIR

def simple_slugify(text):
    text = str(text).lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text

def get_unique_models():
    models = set()
    print("Scanning for car models...")
    if JSON_DATA_DIR.exists():
        for date_dir in os.listdir(JSON_DATA_DIR):
            dir_path = JSON_DATA_DIR / date_dir
            if dir_path.is_dir() and date_dir.startswith('cars_'):
                for item in os.listdir(dir_path):
                    if item.isdigit():
                        json_path = dir_path / item / f"{item}.json"
                        if json_path.exists():
                            try:
                                with open(json_path, 'r') as f:
                                    data = json.load(f)
                                    brand = data.get('brand', {}).get('name')
                                    model = data.get('model')
                                    if brand and model:
                                        models.add((brand, model))
                            except Exception:
                                pass
    return sorted(list(models))


def fetch_review_content(url, source):
    """
    Fetches the content of a review from the given URL.
    Returns a dictionary with 'text' and 'summary' or None if failed.
    """
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if resp.status_code != 200:
            return None
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        content = ""
        summary = ""

        if source == "BilNorge":
            # BilNorge article usually in main_col or article tags
            # Based on inspection, looking for introduction (ingress) and body
            
            # Summary/Ingress
            # Usually h2 or p class="lead" or just h2 under h1
            h1 = soup.find('h1')
            if h1:
                ingress = h1.find_next_sibling(['h2', 'p'])
                if ingress:
                    summary = ingress.get_text(strip=True)
            
            # Content
            # Looking for div with class 'lab-row' or id 'lc-components' or just body text
            article_body = soup.find('div', id='lc-components')
            if not article_body:
                 article_body = soup.find('div', class_='main_col')
            if not article_body:
                article_body = soup.find('body') # Fallback
            
            # Gather text from paragraphs ensuring they look like prose (len > 30)
            ps = article_body.find_all('p')
            content_blocks = []
            for p in ps:
                txt = p.get_text(strip=True)
                if len(txt) > 30:
                    content_blocks.append(txt)
            content = "\n\n".join(content_blocks)
            
        elif source == "Broom":
            # TV2 Broom
            # Usually <div class="article-body"> or similar
            article_body = soup.find('div', class_='article-body') or soup.find('div', {'itemprop': 'articleBody'})
            if article_body:
                ps = article_body.find_all('p')
                content = "\n\n".join([p.get_text(strip=True) for p in ps])
            else:
                 # Fallback
                ps = soup.find_all('p')
                content_blocks = []
                for p in ps:
                    txt = p.get_text(strip=True)
                    if len(txt) > 30:
                        content_blocks.append(txt)
                content = "\n\n".join(content_blocks)
        
        return {
            "summary": summary,
            "text": content
        }

    except Exception as e:
        print(f"Error fetching content from {url}: {e}")
        return None

def search_broom(brand, model):
    query = f"{brand} {model}"
    print(f"  Searching Broom for {query}...")
    # Broom/TV2 search url format (approximate)
    url = f"https://www.tv2.no/broom/sok?q={requests.utils.quote(query)}"
    
    reviews = []
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Look for article links
            for article in soup.find_all('article'):
                link = article.find('a', href=True)
                if link:
                    title = link.get_text(strip=True)
                    href = link['href']
                    if 'test' in title.lower() or 'bruktbil' in title.lower():
                        if not href.startswith('http'):
                            href = "https://www.tv2.no" + href
                        
                        review = {
                            "source": "Broom",
                            "title": title,
                            "url": href
                        }

                        # Fetch content
                        # print(f"    Fetching content for Broom: {title}")
                        content = fetch_review_content(href, "Broom")
                        if content:
                            review.update(content)
                            
                        reviews.append(review)
                        time.sleep(0.5) # Polite delay
    except Exception as e:
        print(f"    Error broom: {e}")
    return reviews[:2] # Limit to top 2 for speed


def get_bilnorge_brand_links():
    print("Fetching BilNorge brand index...")
    links = {}
    try:
        resp = requests.get("https://www.bilnorge.no/biltester", headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                text = a.get_text(strip=True)
                # Look for brand links in the index, they seem to contain 'biltester' and the brand name
                # Heuristic: if text is a single word (mostly) and href contains 'biltester'
                if text and 'biltester' in href:
                    links[text.lower()] = href if href.startswith('http') else "https://www.bilnorge.no" + href
    except Exception as e:
        print(f"Error fetching BilNorge index: {e}")
    return links

BILNORGE_CACHE = {}

def get_bilnorge_reviews_for_brand(brand, brand_links):
    brand_lower = brand.lower()
    if brand_lower not in brand_links:
        return []
    
    if brand_lower in BILNORGE_CACHE:
        return BILNORGE_CACHE[brand_lower]
        
    url = brand_links[brand_lower]
    # print(f"  Fetching BilNorge reviews for {brand}...") # detailed logging
    reviews = []
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Extract articles
            main_col = soup.find('div', class_='main_col') or soup.find('body')
            if main_col:
                for a in main_col.find_all('a', href=True):
                    title = a.get_text(strip=True)
                    href = a['href']
                    if len(title) > 10: # Avoid tiny links
                        if not href.startswith('http'):
                            href = "https://www.bilnorge.no" + href
                        
                        reviews.append({
                            "source": "BilNorge",
                            "title": title,
                            "url": href
                        })
    except Exception as e:
        print(f"    Error processing brand page {brand}: {e}")
    
    BILNORGE_CACHE[brand_lower] = reviews
    return reviews


def search_bilnorge(brand, model, brand_links=None):
    # If we have brand links, use the cache method
    matches = []
    if brand_links and brand.lower() in brand_links:
        all_reviews = get_bilnorge_reviews_for_brand(brand, brand_links)
        model_parts = model.lower().split()
        for rev in all_reviews:
            t = rev['title'].lower()
            # Loose matching: Brand + Model keywords
            if brand.lower() in t and all(p in t for p in model_parts):
                matches.append(rev)
    
    matches = matches[:2] # Limit to top 2
    
    # Enrich with content
    for rev in matches:
        print(f"    Fetching content for BilNorge: {rev['title']}")
        content = fetch_review_content(rev['url'], "BilNorge")
        if content:
            rev.update(content)
        time.sleep(0.5)
        
    return matches

def main():
    if not DATA_REVIEWS_DIR.exists():
        os.makedirs(DATA_REVIEWS_DIR)
        
    models = get_unique_models()
    print(f"Found {len(models)} unique models to check.")

    # 1. Fetch BilNorge Index
    bn_links = get_bilnorge_brand_links()
    print(f"Parsed {len(bn_links)} brands from BilNorge index.")

    for brand, model in models:
        # Use new search methods
        broom_reviews = search_broom(brand, model)
        bilnorge_reviews = search_bilnorge(brand, model, brand_links=bn_links)
        
        all_reviews = broom_reviews + bilnorge_reviews
        
        if not all_reviews:
            # Skip saving if no reviews found
            continue 
            
        print(f"  Found {len(all_reviews)} reviews for {brand} {model}")

        data = {
            "brand": brand,
            "model": model,
            "reviews": all_reviews,
            "last_updated": time.strftime("%Y-%m-%d")
        }
        
        filename = simple_slugify(f"{brand}-{model}") + ".json"
        with open(DATA_REVIEWS_DIR / filename, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        time.sleep(0.5)

if __name__ == "__main__":
    main()
