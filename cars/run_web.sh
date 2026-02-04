#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
echo "Generating webpage..."
python3 -m src.visualization.generate_webpage
