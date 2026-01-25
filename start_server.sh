#!/bin/bash
# Script to start Django development server with virtual environment

cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Run the server
echo "Starting Django development server..."
echo "Press Ctrl+C to stop"
echo ""

python manage.py runserver
