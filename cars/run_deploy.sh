#!/bin/bash
set -e

# Default site name
SITE_NAME="tonys-cars"

# Check for NETLIFY_AUTH_TOKEN
if [ -z "$NETLIFY_AUTH_TOKEN" ]; then
    echo "Error: NETLIFY_AUTH_TOKEN is not set."
    echo "Please generate a Personal Access Token at https://app.netlify.com/user/applications#personal-access-tokens"
    echo "Then run: export NETLIFY_AUTH_TOKEN=your_token_here"
    exit 1
fi

# Check for NETLIFY_SITE_ID, try to find it if not set
if [ -z "$NETLIFY_SITE_ID" ]; then
    echo "NETLIFY_SITE_ID not set. Trying to find site ID for '$SITE_NAME'..."
    
    # List sites and find the ID for tonys-cars
    SITES_RESPONSE=$(curl -s -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" "https://api.netlify.com/api/v1/sites")
    
    # simple python script to parse json
    NETLIFY_SITE_ID=$(echo "$SITES_RESPONSE" | python3 -c "import sys, json; print(next((site['id'] for site in json.load(sys.stdin) if site['name'] == '$SITE_NAME' or site['custom_domain'] == '$SITE_NAME'), ''))")
    
    if [ -z "$NETLIFY_SITE_ID" ]; then
        echo "Error: Could not find site ID for '$SITE_NAME'. Please set NETLIFY_SITE_ID manually."
        exit 1
    else
        echo "Found Site ID: $NETLIFY_SITE_ID"
    fi
fi

# Creation of zip file
echo "Zipping web files..."
# cd into web directory to zip relative paths
cd web
# Remove old zip if exists
rm -f index.zip
# Zip index.html and any index folder
zip -r index.zip index.html index/ 2>/dev/null || zip -r index.zip index.html
cd ..

echo "Deploying to Netlify..."
RESPONSE=$(curl -s -H "Content-Type: application/zip" \
     -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
     --data-binary "@web/index.zip" \
     "https://api.netlify.com/api/v1/sites/$NETLIFY_SITE_ID/deploys")

# Check if deploy was successful (look for valid deploy id or state)
DEPLOY_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))")

if [ -n "$DEPLOY_ID" ]; then
    echo "Deployment successful!"
    echo "Deploy ID: $DEPLOY_ID"
    # Extract deploy URL
    DEPLOY_URL=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('deploy_ssl_url', ''))")
    echo "Live URL: $DEPLOY_URL"
else
    echo "Deployment failed."
    echo "Response: $RESPONSE"
    exit 1
fi
