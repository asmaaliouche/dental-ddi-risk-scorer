.PHONY: install dev lint format test check pipeline verify run clean

# ── Setup ─────────────────────────────────────────────────────────────────────
install:
	poetry install

dev:
	poetry install --with dev

# ── Code quality ──────────────────────────────────────────────────────────────
lint:
	poetry run ruff check src api tests

format:
	poetry run black src api tests
	poetry run isort src api tests

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	poetry run pytest tests/ -v

# ── Run this before every commit ──────────────────────────────────────────────
check: lint test
	@echo "✅  lint + tests passed — safe to commit"

# ── Data pipeline ─────────────────────────────────────────────────────────────
pipeline:
	poetry run python src/ddi_scorer/pipeline.py

score:
	poetry run python src/ddi_scorer/scorer.py

verify:
	poetry run python -c "\
import pandas as pd; \
df = pd.read_parquet('data/processed/interactions.parquet'); \
print(f'Rows: {len(df):,}'); \
print(f'Columns: {list(df.columns)}'); \
print(f'Dental drugs: {sorted(df[\"dental_drug_name\"].dropna().unique())}'); \
print(f'Unique pairs: {df[[\"drug_1_concept_name\",\"drug_2_concept_name\"]].drop_duplicates().shape[0]:,}'); \
"

# ── API ───────────────────────────────────────────────────────────────────────
run:
	poetry run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# ── Utilities ─────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
