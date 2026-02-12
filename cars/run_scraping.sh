#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
echo "Starting scraping..."
python3 -m src.scraping.track_cars

echo "Enriching with Vegvesen/Technical data..."
python3 -m src.scraping.enrich_vegvesen

