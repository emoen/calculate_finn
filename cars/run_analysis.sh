#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Configuration
export OPENROUTER_API_KEY="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"

echo "Training model..."
python3 -m src.analysis.train_model
echo "Ranking cars..."
python3 -m src.analysis.rank_cars
echo "Merging scores..."
python3 -m src.analysis.merge_scores
