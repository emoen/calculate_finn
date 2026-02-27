#!/bin/bash
set -e

# Try to activate virtual environment if not already active
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "../calculate/bin/activate" ]; then
        source ../calculate/bin/activate
    elif [ -f "calculate/bin/activate" ]; then
        source calculate/bin/activate
    fi
fi

export PYTHONPATH=$PYTHONPATH:$(pwd)

LIMIT_ARGS=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --limit) LIMIT_ARGS="--limit $2"; shift ;;
        --test) LIMIT_ARGS="--limit 100" ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

LOG_FILE="execution.log"
> "$LOG_FILE"

echo "Logging output to $LOG_FILE"

echo "=== MODEL CHECK ===" | tee -a "$LOG_FILE"
python3 src/check_models.py 2>&1 | tee -a "$LOG_FILE"

echo "=== STEP 1: SCRAPING ===" | tee -a "$LOG_FILE"
echo "Args: $LIMIT_ARGS" | tee -a "$LOG_FILE"
./run_scraping.sh $LIMIT_ARGS 2>&1 | tee -a "$LOG_FILE"

echo "=== STEP 2: PROCESSING ===" | tee -a "$LOG_FILE"
./run_processing.sh 2>&1 | tee -a "$LOG_FILE"

echo "=== STEP 3: ANALYSIS ===" | tee -a "$LOG_FILE"
./run_analysis.sh 2>&1 | tee -a "$LOG_FILE"

echo "=== STEP 4: VISUALIZATION ===" | tee -a "$LOG_FILE"
./run_web.sh 2>&1 | tee -a "$LOG_FILE"

echo "All tasks completed." | tee -a "$LOG_FILE"

echo ""
echo "============================================"
echo "           EXECUTION SUMMARY                "
echo "============================================"
grep "SUMMARY:" "$LOG_FILE" || true
echo "============================================"
