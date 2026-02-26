#!/bin/bash
set -e

# Try to activate virtual environment if not already active
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "../calculate/bin/activate" ]; then
        source ../calculate/bin/activate
    elif [ -f "calculate/bin/activate" ]; then
        source calculate/bin/activate
    fi
fi

export PYTHONPATH=$PYTHONPATH:$(pwd)

LIMIT_ARGS=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --limit) LIMIT_ARGS="--limit $2"; shift ;;
        --test) LIMIT_ARGS="--limit 10" ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

echo "=== STEP 1: SCRAPING ==="
echo "Args: $LIMIT_ARGS"
./run_scraping.sh $LIMIT_ARGS

echo "=== STEP 2: PROCESSING ==="
./run_processing.sh

echo "=== STEP 3: ANALYSIS ==="
./run_analysis.sh

echo "=== STEP 4: VISUALIZATION ==="
./run_web.sh

echo "All tasks completed."
