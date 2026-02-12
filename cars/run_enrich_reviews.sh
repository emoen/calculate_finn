#!/bin/bash
# Ensure we run from the script's directory
cd "$(dirname "$0")"

# Add current directory to PYTHONPATH so we can import 'src'
export PYTHONPATH=$PYTHONPATH:$(pwd)

echo "Enriching with Reviews..."
python3 -m src.scraping.enrich_reviews
