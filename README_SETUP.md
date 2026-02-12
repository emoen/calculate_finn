# Environment Setup Guide

This project is configured to run in a specific environment. Follow these steps to replicate the environment on a new machine.

## Prerequisites

- Python 3.12 (or compatible version)
- Unix-like environment (Linux/macOS)

## Quick Start

1.  **Clone the repository** to your machine.
2.  **Run the setup script**:
    ```bash
    ./setup_env.sh
    ```
    This script will:
    - Create a virtual environment named `calculate`.
    - Install all Python dependencies from `requirements.txt`.
    - Create necessary empty data directories that are not tracked by git.

## Activation

To start working, activate the virtual environment:

```bash
source calculate/bin/activate
```

## Running Scripts

- **Web Application**:
  ```bash
  python webapp/manage.py runserver
  ```
- **Car Analysis Scripts**:
  Inside the `cars/` directory, use the provided shell scripts:
  ```bash
  cd cars
  ./run_all.sh
  ```

## Automated Tasks (Cron)

The project uses a crontab for automated tasks. The current configuration is stored in the `crontab` file.

**Note**: The default `crontab` uses absolute paths (e.g., `/home/endrem/...`). If your username or project path differs, you must update these paths in the `crontab` file before installing it.

To install the crontab:
```bash
crontab crontab
```

## Troubleshooting

- **Missing Data**: The `json_data/` and `cars/data_json/` folders are initially empty. You may need to run scraping scripts or copy `listings.db` from an existing installation if you need historical data.
