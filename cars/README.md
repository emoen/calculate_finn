# Crazy Tony's Premium Motors

A pipeline that scrapes car listings from FINN.no, enriches them with professional reviews, scores deals using both an ML model and an LLM, and publishes a static website.

**Live site:** [tonys-cars.pages.dev](https://tonys-cars.pages.dev)

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                          PIPELINE                                 │
│                                                                   │
│  ┌──────────┐   ┌────────────┐   ┌──────────┐   ┌─────────────┐ │
│  │ SCRAPING │──▶│ PROCESSING │──▶│ ANALYSIS │──▶│    BUILD    │ │
│  └──────────┘   └────────────┘   └──────────┘   └─────────────┘ │
│       │               │               │               │          │
│  track_cars      populate_db     train_model    build_static_api │
│  enrich_reviews  build_market    rank_cars       generate_webpage│
│                  compress_reviews merge_scores                    │
└───────────────────────────────────────────────────────────────────┘
                                                        │
                                                        ▼
                                              ┌──────────────────┐
                                              │   web/ (static)  │
                                              │  index.html      │
                                              │  api/meta.json   │
                                              │  api/cars/*.json │
                                              └──────────────────┘
                                                        │
                                                        ▼
                                              Cloudflare Pages / Netlify
```

### Module Overview

| Module | Path | Purpose |
|--------|------|---------|
| **config** | `src/config.py` | Central path configuration (`BASE_DIR`, data dirs) |
| **utils** | `src/utils.py` | Shared helpers (`extract_year`, `extract_mileage`, `normalize_brand`) |
| **scraping** | `src/scraping/` | Fetch car listings and reviews from external sites |
| **processing** | `src/processing/` | Store data in SQLite, build market stats, compress reviews via LLM |
| **analysis** | `src/analysis/` | ML model training, LLM car ranking, score merging |
| **build** | `src/build/` | Generate static JSON API files for the frontend |
| **visualization** | `src/visualization/` | Generate legacy monolithic HTML page |

### Data Flow

1. **Scrape** — `track_cars.py` fetches FINN.no listings (JSON-LD + images) into `data_json/cars_DDMMYYYY/`
2. **Enrich** — `enrich_reviews.py` searches Broom and BilNorge for professional reviews → `data_reviews/`
3. **Compress** — `compress_reviews.py` summarizes reviews via LLM into structured JSON → `data_reviews_compressed/`
4. **Process** — `populate_database_cars.py` stores listings in `listings.db`; `build_market_knowledge.py` computes price stats → `data_ranking/market_knowledge.json`
5. **Analyze** — `train_model.py` trains a RandomForest price predictor → `data_ranking/ml_scores.json`; `rank_cars.py` scores each car via LLM → `data_ranking/rankings.json`; `merge_scores.py` combines both
6. **Build** — `build_static_api.py` splits rankings into paginated JSON files → `web/api/`
7. **Deploy** — Upload `web/` directory to Cloudflare Pages or Netlify

### Data Directories

```
cars/
├── data_json/              # Raw scraped listings (one folder per day)
│   └── cars_27032026/
│       └── 452969841/      # Each listing gets its own folder
│           ├── 452969841.json
│           └── image_0.jpg
├── data_reviews/           # Raw review data per model
├── data_reviews_compressed/# LLM-compressed review summaries
├── data_ranking/           # Analysis outputs
│   ├── rankings.json       # LLM deal scores (primary data source)
│   ├── ml_scores.json      # ML model predicted scores
│   ├── market_knowledge.json # Price statistics per model/year/seller
│   └── comparison_scores.json
├── listings.db             # SQLite database of all listings
└── web/                    # Static site (deploy this folder)
    ├── index.html          # SPA frontend
    └── api/
        ├── meta.json       # Pagination metadata + brand list
        └── cars/
            ├── all.json    # Lightweight car list for search/filter
            ├── page-1.json # Full car data (24 per page)
            └── page-N.json
```

---

## Prerequisites

- Python 3.12+
- Virtual environment: `source ../calculate/bin/activate`
- Required packages: `pip install -r ../requirements.txt`
- OpenRouter API key set in `src/analysis/rank_cars.py` and `src/processing/compress_reviews.py`
- For Cloudflare deploy: `npm install -g wrangler && wrangler login`

---

## Commands

All commands should be run from the `cars/` directory with the virtual environment activated.

### Full Pipeline

```bash
# Run everything: scrape → process → analyze → build
./run_all.sh

# Test mode (scrape only 100 listings)
./run_all.sh --test

# Limit to N new listings
./run_all.sh --limit 500
```

### Individual Steps

#### 1. Scraping

```bash
# Scrape new car listings from FINN.no
./run_scraping.sh

# Limit number of new cars to fetch
./run_scraping.sh --limit 200

# Scrape reviews from Broom and BilNorge
./run_enrich_reviews.sh
```

#### 2. Processing

```bash
# Populate SQLite DB + build market statistics
./run_processing.sh

# Compress reviews with LLM (generates structured summaries)
./run_compress_reviews.sh
```

#### 3. Analysis

```bash
# Train ML model + LLM ranking + merge scores
./run_analysis.sh

# Show compressed review scores
./run_show_scores.sh
```

#### 4. Build & Deploy

```bash
# Build static JSON API + legacy HTML page
./run_web.sh

# Deploy to Cloudflare Pages
./run_deploy_cf.sh

# Deploy to Netlify (legacy)
./run_deploy.sh
```

#### Utilities

```bash
# Check LLM model connectivity
python3 src/check_models.py

# Continuous scraping daemon (loops with adaptive delays)
python3 -m src.scraping.do_iterations_cars
```

### Local Development

```bash
# Serve the frontend locally
cd web && python3 -m http.server 8000
# Open http://localhost:8000
```

---

## Frontend

The frontend is a vanilla JS single-page application (`web/index.html`) that fetches pre-built JSON.

**Features:**
- Pagination (24 cars/page)
- Real-time search (name, brand, model, FINN ID)
- Brand dropdown filter
- Score category filter (Steals / Good / Risky)
- Sort by deal score or price
- Modal with full description (lazy-loaded from page JSON)

**No build step required** — it's a single HTML file with inline CSS and JS.

---

## Environment

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENROUTER_API_KEY` | OpenRouter API key for LLM calls | Yes (currently hardcoded) |
| `NETLIFY_AUTH_TOKEN` | Netlify deploy token | Only for `run_deploy.sh` |
| `NETLIFY_SITE_ID` | Netlify site ID | Only for `run_deploy.sh` |

---

## Scoring

Each car receives two scores:

1. **ML Score** — A RandomForest model predicts the "fair market price" based on brand, year, mileage, power, fuel type, and market stats. The ratio of predicted vs. actual price maps to a 0–10 score.

2. **LLM Score** — An LLM analyzes the listing description, market context, and professional review data to rate the deal 0–10.

Both are merged in `comparison_scores.json`. The `rankings.json` (LLM scores) is the primary data source for the frontend.
