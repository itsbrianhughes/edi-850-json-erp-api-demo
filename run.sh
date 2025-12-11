#!/bin/bash

# Quick Start Script for EDI 850 Integration Demo

echo "================================================"
echo "  EDI 850 → JSON → ERP API Integration Demo"
echo "================================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r backend/requirements.txt

# Run FastAPI server
echo ""
echo "Starting FastAPI server..."
echo "API will be available at: http://localhost:8000"
echo "API Docs available at: http://localhost:8000/docs"
echo ""
echo "To view the UI, open frontend/index.html in your browser"
echo ""
echo "Press CTRL+C to stop the server"
echo ""

cd backend
python main.py
