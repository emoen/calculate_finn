#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
echo "Starting scraping..."
# Pass all arguments to track_cars
python3 -m src.scraping.track_cars "$@"

