FROM python:3.12-slim

WORKDIR /app

RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p data/models data/metrics

EXPOSE 8000 8501

CMD ["sh", "-c", "exec bash start.sh ${SERVICE_MODE:-all}"]
