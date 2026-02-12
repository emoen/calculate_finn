#!/bin/bash
# Ensure we run from the script's directory
cd "$(dirname "$0")"

# Add current directory to PYTHONPATH so we can import 'src'
export PYTHONPATH=$PYTHONPATH:$(pwd)

echo "Compressing Reviews with AI..."
python3 -m src.processing.compress_reviews
