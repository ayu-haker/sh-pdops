.PHONY: install run-api run-dashboard test clean simulate

install:
	pip install -r requirements.txt

run-api:
	uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

run-dashboard:
	streamlit run src/dashboard/app.py --server.port 8501

run:
	python -m src.main

test:
	pytest tests/ -v --cov=src

simulate:
	python scripts/simulate.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov

eval:
	python scripts/evaluate.py

lint:
	ruff check src/ tests/
	mypy src/
