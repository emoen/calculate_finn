#!/bin/bash

# Configuration
export OPENROUTER_API_KEY="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"

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Step 1: Update Market Knowledge
echo "Updating market statistics..."
python3 "$SCRIPT_DIR/build_market_knowledge.py"

# Step 2: Run the ranking script
echo "Starting car ranking process using OpenRouter AI..."
python3 "$SCRIPT_DIR/rank_cars.py"
echo "Ranking process completed."
