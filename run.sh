#!/bin/bash
# Usage: ./run.sh [RACE_URL]
# Examples:
#   ./run.sh "https://nar.netkeiba.com/race/result.html?race_id=202542062612"    # Local racing (NAR)
#   ./run.sh "https://race.netkeiba.com/race/result.html?race_id=202509030611"  # Central racing (JRA)

if [ $# -eq 0 ]; then
    echo "Usage: $0 <race_url>"
    echo "Examples:"
    echo "  $0 \"https://nar.netkeiba.com/race/result.html?race_id=202542062612\"    # Local racing (NAR)"
    echo "  $0 \"https://race.netkeiba.com/race/result.html?race_id=202509030611\"  # Central racing (JRA)"
    exit 1
fi

RACE_URL="$1"

echo "Building Docker image..."
docker compose build

echo "Running scraper with URL: $RACE_URL"
RACE_URL="$RACE_URL" docker compose run --rm scraper