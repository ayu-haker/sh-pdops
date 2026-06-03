#!/bin/bash
set -e

echo "SH-PDOPS: Self-Healing + Predictive DevOps System"
echo "================================================"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -q

# Run API server
echo "Starting API server on port 8000..."
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!
echo "API PID: $API_PID"

sleep 2

# Run dashboard
echo "Starting Dashboard on port 8501..."
streamlit run src/dashboard/app.py --server.port 8501 &
DASHBOARD_PID=$!
echo "Dashboard PID: $DASHBOARD_PID"

echo ""
echo "SH-PDOPS is running:"
echo "  API:        http://localhost:8000"
echo "  Docs:       http://localhost:8000/docs"
echo "  Dashboard:  http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop all services"

trap "kill $API_PID $DASHBOARD_PID 2>/dev/null; exit" INT TERM
wait
