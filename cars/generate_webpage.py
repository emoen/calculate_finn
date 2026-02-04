import json
import os
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent
JSON_DATA_DIR = BASE_DIR / 'json_data'
RANKINGS_FILE = BASE_DIR / 'rankings_data' / 'rankings.json'
OUTPUT_FILE = BASE_DIR / 'web' / 'index.html'

def load_data():
    """Load rankings from the central JSON file."""
    if not RANKINGS_FILE.exists():
        print(f"Error: {RANKINGS_FILE} not found!")
        return []
    
    with open(RANKINGS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Convert dict to list of items for sorting
    items = []
    for finn_id, info in data.items():
        items.append((finn_id, info))
        
    # Sort by score descending (highest first)
    items.sort(key=lambda x: float(x[1].get('score', 0)), reverse=True)
    return items

def get_car_details(json_relative_path):
    """
    Fetch image and description from the specific car's scraped JSON.
    The path in rankings.json is usually relative like 'json_data/...'
    """
    if not json_relative_path:
        return {}
    
    full_path = BASE_DIR / json_relative_path
    
    if not full_path.exists():
        # Fallback: The path might be old (wrong date folder). 
        # Search for the same ID in the current JSON contents.
        try:
            # path is like 'json_data/cars_19012026/123/123.json'. Stem is '123'
            finn_id = Path(json_relative_path).stem
            if finn_id.isdigit():
                # Look for 'cars_*/finn_id/finn_id.json' in the actual data dir
                candidates = list(JSON_DATA_DIR.glob(f"cars_*/{finn_id}/{finn_id}.json"))
                if candidates:
                    # Pick one (e.g., the last one found)
                    full_path = candidates[-1]
                    # print(f"Recovered path for {finn_id}: {full_path}")
        except Exception as e:
            # print(f"Fallback search failed: {e}")
            pass
            
    if not full_path.exists():
        return {}
        
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading details for {json_relative_path}: {e}")
        return {}

def generate_html(sorted_items):
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tony's Premium Certified* Pre-Owned (*Certified by Tony)</title>
    <style>
        :root {
            --primary: #2c3e50;
            --secondary: #34495e;
            --accent: #c0392b; /* Sleazy Red */
            --gold: #f1c40f;
            --light: #ecf0f1;
            --dark: #2c3e50;
            --success: #27ae60;
            --card-bg: #ffffff;
        }
        
        body {
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f4f7f6;
            margin: 0;
            padding: 0;
            color: var(--dark);
            line-height: 1.6;
        }
        
        /* Professional Header Structure */
        header {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            padding: 3rem 1rem;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            position: relative;
            overflow: hidden;
        }
        
        header::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background-image: radial-gradient(circle at 20% 50%, rgba(255,255,255,0.05) 0%, transparent 50%);
            pointer-events: none;
        }

        h1 {
            font-size: 3rem;
            margin: 0;
            font-weight: 800;
            letter-spacing: 1px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        h1 span {
            color: var(--gold);
        }

        h2 {
            font-weight: 300;
            font-style: italic;
            opacity: 0.9;
            margin-top: 1rem;
            font-size: 1.4rem;
            font-family: 'Georgia', serif;
        }

        /* The Sleazy Marquee */
        .marquee-container {
            background: var(--accent);
            color: white;
            padding: 12px 0;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.9rem;
            letter-spacing: 1px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .marquee {
            white-space: nowrap;
            overflow: hidden;
            position: relative;
        }
        
        .marquee span {
            display: inline-block;
            padding-left: 100%;
            animation: marquee 25s linear infinite;
        }

        @keyframes marquee {
            0% { transform: translate(0, 0); }
            100% { transform: translate(-100%, 0); }
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 30px 15px;
        }

        /* Filter Controls */
        .filter-bar {
            background: white;
            padding: 15px;
            border-radius: 50px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.05);
            margin-bottom: 40px;
            display: flex;
            justify-content: center;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .filter-btn {
            background: transparent;
            color: var(--secondary);
            font-size: 0.95rem;
            font-weight: 600;
            border: 2px solid transparent;
            padding: 10px 25px;
            cursor: pointer;
            border-radius: 25px;
            transition: all 0.3s ease;
        }
        
        .filter-btn:hover, .filter-btn.active {
            background: var(--light);
            border-color: var(--primary);
            color: var(--primary);
        }

        /* Grid System */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 40px;
        }

        /* Professional Card Design */
        .card {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.3s ease;
            position: relative;
            display: flex;
            flex-direction: column;
            border: 1px solid rgba(0,0,0,0.05);
            cursor: pointer;
        }

        .card:hover {
            transform: translateY(-8px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.12);
        }

        .card-header {
            position: relative;
            height: 220px;
            overflow: hidden;
        }

        .card-image {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.5s ease;
        }

        .card:hover .card-image {
            transform: scale(1.05);
        }

        .score-badge {
            position: absolute;
            top: 15px;
            right: 15px;
            width: 45px;
            height: 45px;
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(5px);
            color: var(--dark);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 900;
            font-size: 1.2rem;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            z-index: 2;
            border: 2px solid var(--gold);
        }

        .status-badge {
            position: absolute;
            top: 15px;
            left: 15px;
            padding: 5px 12px;
            border-radius: 4px;
            color: white;
            font-size: 0.75rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            z-index: 2;
        }
        
        .status-high { background-color: var(--success); }
        .status-mid { background-color: #f39c12; }
        .status-low { background-color: var(--accent); }
        .status-pending { background-color: #7f8c8d; }

        .card-body {
            padding: 25px;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
        }

        .title {
            font-size: 1.2rem;
            font-weight: 700;
            color: var(--dark);
            margin-bottom: 10px;
            line-height: 1.3;
        }

        .price {
            font-size: 1.6rem;
            font-weight: 800;
            color: var(--accent);
            margin-bottom: 15px;
        }
        
        .divider {
            height: 1px;
            background: #eee;
            margin: 10px 0 20px 0;
        }

        .reason {
            font-size: 0.95rem;
            color: #666;
            line-height: 1.5;
            font-style: italic;
            margin-bottom: 20px;
        }

        .meta {
            margin-top: auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.8rem;
            color: #aaa;
        }
        
        .view-btn {
            background: var(--dark);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        .view-btn:hover { background: var(--accent); }

        /* Modal Styles */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            backdrop-filter: blur(5px);
            padding: 20px;
        }

        .modal-content {
            background: white;
            border-radius: 12px;
            width: 100%;
            max-width: 900px;
            max-height: 90vh;
            overflow-y: auto;
            position: relative;
            box-shadow: 0 25px 50px rgba(0,0,0,0.25);
            animation: slideUp 0.3s ease-out;
            display: flex;
            flex-direction: column;
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .modal-header-area {
            padding: 25px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }

        .close-btn {
            font-size: 1.5rem;
            cursor: pointer;
            color: #999;
            transition: color 0.2s;
            line-height: 1;
        }
        
        .close-btn:hover { color: var(--accent); }
        
        .modal-body {
            padding: 30px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        
        @media (max-width: 768px) {
            .modal-body { grid-template-columns: 1fr; }
        }

        .cta-btn {
            display: block;
            background: var(--success);
            color: white;
            text-align: center;
            padding: 15px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: bold;
            font-size: 1.1rem;
            text-transform: uppercase;
            margin-top: 20px;
            transition: all 0.2s;
            box-shadow: 0 4px 15px rgba(39, 174, 96, 0.3);
        }
        
        .cta-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(39, 174, 96, 0.4);
            background: #219150;
        }
    </style>
</head>
<body>

    <header>
        <h1>CRAZY TONY'S <span>PREMIUM</span> MOTORS</h1>
        <h2>"We Lose Money On Every Sale! (Tax Reasons!)"</h2>
    </header>

    <div class="marquee-container">
        <div class="marquee">
            <span>
            📣 BANKRUPTCY SALE? DIVORCE SETTLEMENT? WE DON'T ASK, WE JUST SELL! 
            &nbsp;&nbsp;&bull;&nbsp;&nbsp; 
            NO CREDIT? BAD CREDIT? WE ACCEPT CASH, GOLD, AND PROBABLY CRYPTO! 
            &nbsp;&nbsp;&bull;&nbsp;&nbsp; 
            PRICES SO LOW IT'S SUSPICIOUS! 
            &nbsp;&nbsp;&bull;&nbsp;&nbsp; 
            WARRANTY: 30 SECONDS OR 30 FEET (WHICHEVER COMES FIRST)!
            </span>
        </div>
    </div>

    <div class="container">
        <div class="filter-bar">
            <button class="filter-btn active" onclick="filterCards('all')">All Inventory</button>
            <button class="filter-btn" onclick="filterCards('status-high')">Manager's Special (8-10)</button>
            <button class="filter-btn" onclick="filterCards('status-mid')">Daily Drivers (5-7)</button>
            <button class="filter-btn" onclick="filterCards('status-low')">Mechanic's Special (0-4)</button>
        </div>

        <div class="grid">
    """

    for finn_id, data in sorted_items:
        score = data.get('score', 0)
        try:
             score_float = float(score)
        except:
             score_float = 0
             
        name = data.get('name', 'MYSTERY MACHINE')
        price = data.get('price', 'CALL US!')
        reason = data.get('reason', 'IT JUST WORKS!')
        url = data.get('url', '#')
        
        # Get extra details from JSON file
        details_path = data.get('path', '')
        # Handle cases where path might be relative to script dir or workspace
        details = get_car_details(details_path)
        
        image_url = details.get('image', 'https://upload.wikimedia.org/wikipedia/commons/a/ac/No_image_available.svg')
        
        # Handle list of images (common in JSON-LD)
        if isinstance(image_url, list):
            if len(image_url) > 0:
                image_url = image_url[0]
            else:
                image_url = 'https://upload.wikimedia.org/wikipedia/commons/a/ac/No_image_available.svg'
        
        # Handle ImageObject (dict)
        if isinstance(image_url, dict):
            image_url = image_url.get('url', image_url.get('contentUrl', 'https://upload.wikimedia.org/wikipedia/commons/a/ac/No_image_available.svg'))
                
        description = details.get('description', 'No description available. Trust us, it runs.')
        
        score_class = "status-mid"
        badge_text = "Good Deal"
        if score_float >= 8:
            score_class = "status-high"
            badge_text = "STEAL!"
        elif score_float <= 4:
            score_class = "status-low"
            badge_text = "LEMON?"

        # Sanitize image URL
        if not image_url.startswith('http'):
            image_url = 'https://upload.wikimedia.org/wikipedia/commons/a/ac/No_image_available.svg'

        html_content += f"""
        <div class="card {score_class}" onclick="openModal('{finn_id}')">
            <div class="status-badge {score_class}">{badge_text}</div>
            <div class="card-header">
                <div class="score-badge">{score}</div>
                <img src="{image_url}" class="card-image" loading="lazy" alt="{name}" onerror="this.src='https://upload.wikimedia.org/wikipedia/commons/a/ac/No_image_available.svg'">
            </div>
            
            <div class="card-body">
                <div class="title">{name}</div>
                <div class="price">{price} NOK</div>
                <div class="divider"></div>
                <div class="reason">"{reason}"</div>
                
                <div class="meta">
                    <span>ID: {finn_id}</span>
                    <button class="view-btn">VIEW DETAILS</button>
                </div>
            </div>
        </div>

        <!-- Hidden data for modal -->
        <div id="data-{finn_id}" style="display:none;">
            <div class="d-img">{image_url}</div>
            <div class="d-title">{name}</div>
            <div class="d-price">{price} NOK</div>
            <div class="d-reason">{reason}</div>
            <div class="d-desc">{description}</div>
            <div class="d-url">{url}</div>
            <div class="d-score">{score}</div>
        </div>
        """

    html_content += """
        </div>
    </div>

    <!-- Modal implementation -->
    <div id="itemModal" class="modal" onclick="if(event.target === this) closeModal()">
        <div class="modal-content">
            <div class="modal-header-area">
                <div>
                     <h2 id="m-title" style="margin:0; font-weight:800; color:var(--primary);">TITLE</h2>
                     <div id="m-price" style="font-size:1.5rem; color:var(--accent); font-weight:bold; margin-top:5px;">PRICE</div>
                </div>
                <span class="close-btn" onclick="closeModal()">×</span>
            </div>
            
            <div class="modal-body">
                <div>
                    <img id="m-image" src="" style="width:100%; border-radius:8px; box-shadow:0 4px 10px rgba(0,0,0,0.1);">
                    <div style="margin-top:20px; padding:15px; background:var(--light); border-radius:8px; border-left:4px solid var(--accent);">
                        <strong>Tony's Analysis:</strong> <span id="m-reason" style="font-style:italic;">Reason</span>
                    </div>
                </div>
                
                <div style="display:flex; flex-direction:column;">
                    <h3 style="margin-top:0;">Details</h3>
                    <p id="m-desc" style="flex-grow:1; overflow-y:auto; max-height:300px; color:#555;">Description</p>
                    <a id="m-url" href="#" target="_blank" class="cta-btn">BUY IT BEFORE I CHANGE MY MIND!</a>
                </div>
            </div>
        </div>
    </div>

    <script>
        function filterCards(type) {
            // Update active button
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');

            const cards = document.querySelectorAll('.card');
            cards.forEach(card => {
                if (type === 'all') {
                    card.style.display = 'flex';
                } else {
                    if (card.classList.contains(type)) {
                        card.style.display = 'flex';
                    } else {
                        card.style.display = 'none';
                    }
                }
            });
        }

        function openModal(id) {
            const data = document.getElementById('data-' + id);
            
            document.getElementById('m-title').innerText = data.querySelector('.d-title').innerText;
            document.getElementById('m-image').src = data.querySelector('.d-img').innerText;
            document.getElementById('m-price').innerText = data.querySelector('.d-price').innerText;
            document.getElementById('m-desc').innerText = data.querySelector('.d-desc').innerText;
            document.getElementById('m-reason').innerText = data.querySelector('.d-reason').innerText;
            document.getElementById('m-url').href = data.querySelector('.d-url').innerText;
            
            const modal = document.getElementById('itemModal');
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden'; // Prevent scrolling background
        }

        function closeModal() {
            document.getElementById('itemModal').style.display = 'none';
            document.body.style.overflow = 'auto';
        }
        
        // Close on escape key
        document.addEventListener('keydown', function(event) {
            if (event.key === "Escape") {
                closeModal();
            }
        });
    </script>
</body>
</html>
"""

    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Web page generated successfully at: {OUTPUT_FILE}")
    except Exception as e:
        print(f"Failed to write HTML file: {e}")

if __name__ == "__main__":
    rankings = load_data()
    print(f"Loaded {len(rankings)} cars.")
    generate_html(rankings)
