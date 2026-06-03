#!/bin/bash
set -e

# SH-PDOPS Railway entrypoint
# Starts the API server (and optionally dashboard in same container)

MODE="${1:-api}"

case "$MODE" in
  api)
    echo "Starting SH-PDOPS API server..."
    exec uvicorn src.main:app \
      --host 0.0.0.0 \
      --port "${PORT:-8000}" \
      --workers "${API_WORKERS:-1}" \
      --log-level info
    ;;
  dashboard)
    echo "Starting SH-PDOPS Dashboard..."
    exec streamlit run src/dashboard/app.py \
      --server.port "${DASHBOARD_PORT:-8501}" \
      --server.address 0.0.0.0 \
      --server.headless true \
      --browser.gatherUsageStats false
    ;;
  all)
    echo "Starting SH-PDOPS API + Dashboard (single container)..."
    uvicorn src.main:app \
      --host 0.0.0.0 \
      --port "${PORT:-8000}" \
      --workers 1 \
      --log-level info &
    API_PID=$!
    streamlit run src/dashboard/app.py \
      --server.port "${DASHBOARD_PORT:-8501}" \
      --server.address 0.0.0.0 \
      --server.headless true \
      --browser.gatherUsageStats false &
    DASHBOARD_PID=$!
    trap "kill $API_PID $DASHBOARD_PID 2>/dev/null; exit" INT TERM
    wait
    ;;
  *)
    echo "Usage: $0 {api|dashboard|all}"
    exit 1
    ;;
esac
