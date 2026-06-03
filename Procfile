# Procfile for Railway Nixpacks (fallback if Docker not used)
web: uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --log-level info
dashboard: streamlit run src/dashboard/app.py --server.port ${DASHBOARD_PORT:-8501} --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false
