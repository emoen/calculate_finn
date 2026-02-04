import os
from pathlib import Path

# This file is located in cars/src/config.py
# BASE_DIR should point to the 'cars' folder (grandparent of this file)
SRC_DIR = Path(__file__).resolve().parent
BASE_DIR = SRC_DIR.parent

# Define common data directories
JSON_DATA_DIR = BASE_DIR / "json_data"
RANKINGS_DATA_DIR = BASE_DIR / "rankings_data"
WEB_DIR = BASE_DIR / "web"

def get_base_dir():
    return str(BASE_DIR)

def get_json_data_dir():
    return str(JSON_DATA_DIR)
