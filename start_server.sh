#!/bin/bash
# Script to start Django development server with virtual environment

cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Run the server
# Use --noreload if the server seems to hang after "System check identified no issues"
# (avoids slow file watcher; you'll need to restart manually after code changes)
echo "Starting Django development server..."
echo "Press Ctrl+C to stop"
echo ""

python manage.py runserver "$@"
