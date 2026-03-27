#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
echo "Building static JSON API..."
python3 -m src.build.build_static_api
echo "Generating legacy webpage..."
python3 -m src.visualization.generate_webpage
