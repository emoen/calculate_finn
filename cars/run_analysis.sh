#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
echo "Training model..."
python3 -m src.analysis.train_model
echo "Ranking cars..."
python3 -m src.analysis.rank_cars
echo "Merging scores..."
python3 -m src.analysis.merge_scores
