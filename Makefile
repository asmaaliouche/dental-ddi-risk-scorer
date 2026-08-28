.PHONY: install dev lint format test check pipeline score verify run dev-ui smoke clean

# ─────────────────────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────────────────────
install:
	poetry install

dev:
	poetry install --with dev

# ─────────────────────────────────────────────────────────────────────────────
# Code Quality
# ─────────────────────────────────────────────────────────────────────────────
lint:
	poetry run ruff check src api tests scripts

format:
	poetry run black src api tests scripts
	poetry run isort src api tests scripts

# Run lint + tests — execute before every commit
check: lint test
	@echo "✅  lint + tests passed — safe to commit"

# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────
test:
	poetry run pytest tests/ -v

# ─────────────────────────────────────────────────────────────────────────────
# Data Pipeline  (requires raw data — see README)
# ─────────────────────────────────────────────────────────────────────────────
pipeline:
	poetry run python src/ddi_scorer/pipeline.py

score:
	poetry run python src/ddi_scorer/scorer.py

verify:
	@poetry run python -c "\
import pandas as pd; \
df = pd.read_parquet('data/processed/scores.parquet'); \
print(f'Scored pairs: {len(df):,}'); \
print('Severity breakdown:'); \
print(df['severity_bin'].value_counts().to_string()); \
print(f'Top 5 risk scores:'); \
print(df.nlargest(5, 'risk_score')[['dental_drug_name','patient_drug_name','risk_score','severity_bin']].to_string()); \
"

# ─────────────────────────────────────────────────────────────────────────────
# API Backend
# ─────────────────────────────────────────────────────────────────────────────
run:
	poetry run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# ─────────────────────────────────────────────────────────────────────────────
# Frontend  (requires Node.js — see scripts/get_node.py if not installed)
# ─────────────────────────────────────────────────────────────────────────────
NODE_BIN := $(shell which node 2>/dev/null || echo "node")
NPM      := $(NODE_BIN:%/node=%/npm)

dev-ui:
	cd frontend && npm run dev

build-ui:
	cd frontend && npm run build

# ─────────────────────────────────────────────────────────────────────────────
# Integration Smoke Test
# ─────────────────────────────────────────────────────────────────────────────
smoke:
	poetry run python scripts/smoke_test.py

# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	find . -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
