FROM python:3.12-slim

WORKDIR /app

RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p data/models data/metrics

EXPOSE 8000 8501

CMD ["sh", "-c", "if [ \"$SERVICE_MODE\" = \"dashboard\" ]; then exec streamlit run src/dashboard/app.py --server.port ${PORT:-8000} --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false; else exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${API_WORKERS:-1} --log-level info; fi"]
