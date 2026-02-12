#!/bin/bash
set -e
export PYTHONPATH=$PYTHONPATH:$(pwd)

echo "=== STEP 1: SCRAPING ==="
./run_scraping.sh

echo "=== STEP 2: PROCESSING ==="
./run_processing.sh

echo "=== STEP 3: ANALYSIS ==="
./run_analysis.sh

echo "=== STEP 4: VISUALIZATION ==="
./run_web.sh

echo "All tasks completed."
