#!/bin/bash

# Create virtual environment named 'calculate' to match existing project structure
if [ ! -d "calculate" ]; then
    echo "Creating virtual environment 'calculate'..."
    python3 -m venv calculate
else
    echo "Virtual environment 'calculate' already exists."
fi

# Upgrade pip
./calculate/bin/python3 -m pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
./calculate/bin/python3 -m pip install -r requirements.txt

# Create necessary directories that are gitignored but needed for execution
echo "Creating data directories..."
mkdir -p json_data
mkdir -p cars/data_json
mkdir -p cars/data_reviews_compressed
mkdir -p cars/web

echo "Environment setup complete in 'calculate' directory."
echo "You can now activate the environment with: source calculate/bin/activate"
