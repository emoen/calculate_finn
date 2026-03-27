#!/bin/bash
set -e

PROJECT_NAME="tonys-cars"
DEPLOY_DIR="web"

# ── Check for wrangler ──
if ! command -v wrangler &> /dev/null; then
    echo "Error: 'wrangler' CLI not found."
    echo "Install it with: npm install -g wrangler"
    echo "Then authenticate: wrangler login"
    exit 1
fi

# ── Ensure the static API has been built ──
if [ ! -f "$DEPLOY_DIR/api/meta.json" ]; then
    echo "Error: Static API not found at $DEPLOY_DIR/api/"
    echo "Run ./run_web.sh first to generate the API files."
    exit 1
fi

# ── Deploy ──
echo "Deploying $DEPLOY_DIR/ to Cloudflare Pages project '$PROJECT_NAME'..."

# wrangler pages deploy uploads the entire directory as a new deployment.
# First run will prompt to create the project if it doesn't exist.
wrangler pages deploy "$DEPLOY_DIR" --project-name="$PROJECT_NAME"

echo ""
echo "Deploy complete!"
echo "Your site: https://${PROJECT_NAME}.pages.dev"
