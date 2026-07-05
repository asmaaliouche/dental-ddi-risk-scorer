.PHONY: install dev lint format test run clean

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

# ── API ───────────────────────────────────────────────────────────────────────
run:
	poetry run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# ── Utilities ─────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
