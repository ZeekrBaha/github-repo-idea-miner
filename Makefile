.PHONY: install lint format typecheck test check

install:
	uv sync

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy

test:
	uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=90

check: lint typecheck test
	uv run ruff format --check .
