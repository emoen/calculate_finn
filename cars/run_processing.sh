#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
echo "Populating database..."
python3 -m src.processing.populate_database_cars
echo "Building market knowledge..."
python3 -m src.processing.build_market_knowledge
